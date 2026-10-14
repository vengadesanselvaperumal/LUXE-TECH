import os
import sys
import re
import inspect
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.abspath("backend"))

from app.database import (
    Base, User, Trend, TrendSignal, TrendDNA, ImageRecord,
    Collection, Product, RetailSignal, Forecast, Prophecy, SavedTrend
)

print("=" * 80)
print("1. ACTUAL SQLALCHEMY MODELS & METADATA")
print("=" * 80)

orm_models = {
    "users": User,
    "trends": Trend,
    "trend_signals": TrendSignal,
    "trend_dna": TrendDNA,
    "images": ImageRecord,
    "collections": Collection,
    "products": Product,
    "retail_signals": RetailSignal,
    "forecasts": Forecast,
    "prophecy": Prophecy,
    "saved_trends": SavedTrend
}

print(f"Total ORM tables in Base.metadata.tables: {len(Base.metadata.tables)}")
total_cols = sum(len(t.columns) for t in Base.metadata.tables.values())
print(f"Total ORM columns across all tables: {total_cols}")

for name, table in sorted(Base.metadata.tables.items()):
    model_cls = orm_models.get(name)
    cls_name = model_cls.__name__ if model_cls else "UNKNOWN"
    print(f"\nTable: public.{name} (Model: {cls_name}, Columns: {len(table.columns)})")
    for col in table.columns:
        pk_str = " [PK]" if col.primary_key else ""
        fk_str = f" [FK -> {list(col.foreign_keys)[0].target_fullname}]" if col.foreign_keys else ""
        nullable_str = "NULL" if col.nullable else "NOT NULL"
        default_str = f" DEFAULT {col.default.arg}" if col.default and hasattr(col.default, 'arg') else ""
        server_def_str = f" SERVER_DEFAULT {col.server_default.arg}" if col.server_default and hasattr(col.server_default, 'arg') else ""
        print(f"  - {col.name:25} {str(col.type):20} {nullable_str:10}{pk_str}{fk_str}{default_str}{server_def_str}")

print("\n" + "=" * 80)
print("2. CHECK FOR HALLUCINATED TABLE NAMES IN BACKEND")
print("=" * 80)

hallucinated = [
    "fashion_trends", "forecast_metrics", "prophecy_records",
    "design_recommendations", "export_jobs", "api_usage_metrics", "system_logs"
]

occurrences = {h: [] for h in hallucinated}
for root, dirs, files in os.walk("backend"):
    if any(p in root for p in ["venv", "__pycache__", ".pytest_cache"]):
        continue
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8", errors="ignore") as fl:
                c = fl.read()
                for h in hallucinated:
                    if h in c:
                        occurrences[h].append(p)

for h, flist in occurrences.items():
    print(f"  '{h}': {flist if flist else '0 occurrences (NOT in backend code)'}")

print("\n" + "=" * 80)
print("3. PARSE SQL PROPOSALS (PHASE 16 vs PHASE 18)")
print("=" * 80)

def parse_sql_tables(sql_path):
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Find CREATE TABLE statements
    pattern = r"CREATE\s+TABLE\s+(?:public\.)?([a-zA-Z0-9_]+)\s*\((.*?)\);\s*(?:CREATE|ALTER|GRANT|REVOKE|COMMIT|DO|BEGIN|--|\Z)"
    matches = re.findall(r"CREATE\s+TABLE\s+(?:public\.)?([a-zA-Z0-9_]+)\s*\((.*?)\);", sql, re.DOTALL)
    
    tables = {}
    for table_name, body in matches:
        # Parse column definitions
        lines = [line.strip() for line in body.split("\n") if line.strip() and not line.strip().startswith("--")]
        col_defs = []
        for line in lines:
            line = re.sub(r",\s*$", "", line)
            if line.upper().startswith("CONSTRAINT"):
                continue
            parts = line.split()
            if parts:
                col_name = parts[0]
                col_type = parts[1] if len(parts) > 1 else ""
                col_defs.append((col_name, line))
        tables[table_name] = col_defs
    return tables

p16_path = "supabase/proposals/luxe_phase16_canonical_first_install.sql"
p18_path = "supabase/proposals/luxe_phase18_hardened_first_install.sql"

p16_tables = parse_sql_tables(p16_path)
p18_tables = parse_sql_tables(p18_path)

print(f"Phase 16 tables: {sorted(p16_tables.keys())} (Count: {len(p16_tables)})")
print(f"Phase 18 tables: {sorted(p18_tables.keys())} (Count: {len(p18_tables)})")
print(f"ORM tables:      {sorted(Base.metadata.tables.keys())} (Count: {len(Base.metadata.tables)})")

# Check if table names match
p16_diff = set(p16_tables.keys()) ^ set(Base.metadata.tables.keys())
p18_diff = set(p18_tables.keys()) ^ set(Base.metadata.tables.keys())
print(f"Phase 16 vs ORM table name symmetric difference: {p16_diff}")
print(f"Phase 18 vs ORM table name symmetric difference: {p18_diff}")

print("\n" + "=" * 80)
print("4. COLUMN-BY-COLUMN COMPARISON ACROSS ALL 11 TABLES")
print("=" * 80)

for table_name in sorted(Base.metadata.tables.keys()):
    orm_cols = {c.name: c for c in Base.metadata.tables[table_name].columns}
    p16_col_names = [c[0] for c in p16_tables.get(table_name, [])]
    p18_col_names = [c[0] for c in p18_tables.get(table_name, [])]
    
    p16_missing = set(orm_cols.keys()) - set(p16_col_names)
    p16_extra = set(p16_col_names) - set(orm_cols.keys())
    p18_missing = set(orm_cols.keys()) - set(p18_col_names)
    p18_extra = set(p18_col_names) - set(orm_cols.keys())
    
    status = "EXACT MATCH" if not p16_missing and not p16_extra and not p18_missing and not p18_extra else "MISMATCH"
    print(f"Table '{table_name}': ORM={len(orm_cols)}, P16={len(p16_col_names)}, P18={len(p18_col_names)} -> {status}")
    if p16_missing or p16_extra or p18_missing or p18_extra:
        print(f"  P16 Missing: {p16_missing}, Extra: {p16_extra}")
        print(f"  P18 Missing: {p18_missing}, Extra: {p18_extra}")

