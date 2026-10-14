"""Compare the reviewed PostgreSQL proposal with SQLAlchemy metadata offline."""

import os
import re
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.database import Base


proposal_path = project_root / "supabase" / "proposals" / "luxe_canonical_initial_schema_proposal.sql"
sql = proposal_path.read_text(encoding="utf-8")
errors = []


def normalize(value):
    normalized = re.sub(r"\s+", " ", value.strip().lower()).rstrip(";")
    return {
        "timestamptz": "timestamp with time zone",
        "float": "double precision",
    }.get(normalized, normalized)


def split_definitions(block):
    definitions = []
    depth = 0
    start = 0
    for position, character in enumerate(block):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == "," and depth == 0:
            definitions.append(block[start:position].strip())
            start = position + 1
    definitions.append(block[start:].strip())
    return [item for item in definitions if item]


def parse_tables(source):
    parsed = {}
    pattern = re.compile(
        r"CREATE\s+TABLE\s+public\.(\w+)\s*\((.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(source):
        table_name, block = match.groups()
        columns = {}
        unique_sets = set()
        primary_key = set()
        foreign_keys = set()
        for definition in split_definitions(block):
            constraint = re.match(
                r"(?:CONSTRAINT\s+\w+\s+)?(PRIMARY\s+KEY|UNIQUE)\s*\(([^)]+)\)",
                definition,
                re.IGNORECASE,
            )
            if constraint:
                names = tuple(part.strip().strip('"') for part in constraint.group(2).split(","))
                if constraint.group(1).upper().startswith("PRIMARY"):
                    primary_key.update(names)
                else:
                    unique_sets.add(frozenset(names))
                continue
            column_match = re.match(r"(\w+)\s+(.+)", definition, re.DOTALL)
            if not column_match:
                errors.append(f"{table_name}: cannot parse definition {definition!r}")
                continue
            column_name, rest = column_match.groups()
            type_match = re.match(r"(DOUBLE\s+PRECISION|TIMESTAMPTZ|VARCHAR|TEXT|INTEGER)\b", rest, re.IGNORECASE)
            if not type_match:
                errors.append(f"{table_name}.{column_name}: unsupported proposal type")
                continue
            sql_type = normalize(type_match.group(1))
            default_match = re.search(
                r"\sDEFAULT\s+(.+?)(?=\s+(?:NOT\s+NULL|NULL|UNIQUE|REFERENCES|CHECK)\b|$)",
                rest,
                re.IGNORECASE,
            )
            reference_match = re.search(
                r"REFERENCES\s+public\.(\w+)\s*\(\s*(\w+)\s*\)(?:\s+ON\s+DELETE\s+(CASCADE|SET\s+NULL|RESTRICT|NO\s+ACTION))?",
                rest,
                re.IGNORECASE,
            )
            columns[column_name] = {
                "type": sql_type,
                "nullable": not bool(
                    re.search(r"\bNOT\s+NULL\b", rest, re.IGNORECASE)
                    or re.search(r"\bPRIMARY\s+KEY\b", rest, re.IGNORECASE)
                ),
                "default": normalize(default_match.group(1)) if default_match else None,
            }
            if re.search(r"\bPRIMARY\s+KEY\b", rest, re.IGNORECASE):
                primary_key.add(column_name)
            if re.search(r"\bUNIQUE\b", rest, re.IGNORECASE):
                unique_sets.add(frozenset((column_name,)))
            if reference_match:
                target_table, target_column, on_delete = reference_match.groups()
                foreign_keys.add(
                    (column_name, target_table, target_column, (on_delete or "NO ACTION").upper())
                )
        parsed[table_name] = {
            "columns": columns,
            "primary_key": primary_key,
            "unique_sets": unique_sets,
            "foreign_keys": foreign_keys,
        }
    return parsed


proposal_tables = parse_tables(sql)
model_tables = Base.metadata.tables
if set(proposal_tables) != set(model_tables):
    errors.append(
        f"table set differs: proposal-only={sorted(set(proposal_tables) - set(model_tables))}; "
        f"model-only={sorted(set(model_tables) - set(proposal_tables))}"
    )

for table_name in sorted(set(proposal_tables) & set(model_tables)):
    proposal = proposal_tables[table_name]
    model = model_tables[table_name]
    proposal_columns = proposal["columns"]
    model_columns = {column.name: column for column in model.columns}
    if set(proposal_columns) != set(model_columns):
        errors.append(
            f"{table_name}: column set differs; proposal-only="
            f"{sorted(set(proposal_columns) - set(model_columns))}; model-only="
            f"{sorted(set(model_columns) - set(proposal_columns))}"
        )
    for column_name in sorted(set(proposal_columns) & set(model_columns)):
        actual = proposal_columns[column_name]
        expected = model_columns[column_name]
        expected_type = normalize(expected.type.compile(dialect=postgresql.dialect()))
        if actual["type"] != expected_type:
            errors.append(f"{table_name}.{column_name}: type {actual['type']} != ORM {expected_type}")
        if actual["nullable"] != expected.nullable:
            errors.append(f"{table_name}.{column_name}: nullability differs")
        expected_default = normalize(str(expected.server_default.arg)) if expected.server_default else None
        if actual["default"] != expected_default:
            errors.append(
                f"{table_name}.{column_name}: default {actual['default']!r} != "
                f"ORM server default {expected_default!r}"
            )

    expected_pk = {column.name for column in model.primary_key.columns}
    if proposal["primary_key"] != expected_pk:
        errors.append(f"{table_name}: primary key differs")

    expected_uniques = {
        frozenset(column.name for column in constraint.columns)
        for constraint in model.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    expected_uniques.update(
        frozenset((column.name,))
        for column in model.columns
        if column.unique and not column.index
    )
    expected_uniques.update(
        frozenset(column.name for column in index.columns)
        for index in model.indexes
        if index.unique
    )
    actual_unique_indexes = {
        frozenset(columns.split(","))
        for unique, _, index_table, columns in re.findall(
            r"CREATE\s+(UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+public\.(\w+)\s*\(([^)]+)\)",
            sql,
            re.IGNORECASE,
        )
        if unique and index_table == table_name
    }
    actual_uniques = proposal["unique_sets"] | actual_unique_indexes
    if actual_uniques != expected_uniques:
        errors.append(
            f"{table_name}: unique constraints differ; "
            f"proposal={sorted(map(sorted, actual_uniques))}; "
            f"ORM={sorted(map(sorted, expected_uniques))}"
        )

    expected_fks = set()
    for column in model.columns:
        for foreign_key in column.foreign_keys:
            expected_fks.add(
                (
                    column.name,
                    foreign_key.column.table.name,
                    foreign_key.column.name,
                    (foreign_key.ondelete or "NO ACTION").upper(),
                )
            )
    if proposal["foreign_keys"] != expected_fks:
        errors.append(f"{table_name}: foreign keys or delete actions differ")

expected_indexes = {
    (table.name, index.name, tuple(column.name for column in index.columns), index.unique)
    for table in model_tables.values()
    for index in table.indexes
}
actual_indexes = set()
for unique, index_name, table_name, columns in re.findall(
    r"CREATE\s+(UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+public\.(\w+)\s*\(([^)]+)\)",
    sql,
    re.IGNORECASE,
):
    actual_indexes.add(
        (
            table_name,
            index_name,
            tuple(column.strip() for column in columns.split(",")),
            bool(unique),
        )
    )
if actual_indexes != expected_indexes:
    errors.append(
        f"indexes differ; proposal-only={sorted(actual_indexes - expected_indexes)}; "
        f"ORM-only={sorted(expected_indexes - actual_indexes)}"
    )

expected_rls = set(model_tables)
actual_rls = set(
    re.findall(r"ALTER\s+TABLE\s+public\.(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", sql, re.IGNORECASE)
)
if actual_rls != expected_rls:
    errors.append(f"RLS table set differs: proposal={sorted(actual_rls)}; ORM={sorted(expected_rls)}")

if errors:
    print("Schema proposal parity: FAIL")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

column_count = sum(len(table.columns) for table in model_tables.values())
print(
    f"Schema proposal parity: PASS ({len(model_tables)} tables, {column_count} columns, "
    f"{len(expected_indexes)} indexes, {len(expected_rls)} RLS-enabled tables)"
)
