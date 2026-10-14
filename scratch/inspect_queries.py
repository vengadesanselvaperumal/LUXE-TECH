import os
import sys
import ast
import re

sys.path.insert(0, os.path.abspath("backend"))
from app.database import Base

orm_tables = Base.metadata.tables

# Scan all python files in backend/app
backend_app = "backend/app"

all_files = []
for root, dirs, files in os.walk(backend_app):
    if "__pycache__" in root:
        continue
    for f in files:
        if f.endswith(".py"):
            all_files.append(os.path.join(root, f))

print(f"Total files in backend/app: {len(all_files)}")

# Check for model imports and usages
model_names = [
    "User", "Trend", "TrendSignal", "TrendDNA", "ImageRecord",
    "Collection", "Product", "RetailSignal", "Forecast", "Prophecy", "SavedTrend"
]

table_to_model = {
    "users": "User",
    "trends": "Trend",
    "trend_signals": "TrendSignal",
    "trend_dna": "TrendDNA",
    "images": "ImageRecord",
    "collections": "Collection",
    "products": "Product",
    "retail_signals": "RetailSignal",
    "forecasts": "Forecast",
    "prophecy": "Prophecy",
    "saved_trends": "SavedTrend"
}

model_to_table = {v: k for k, v in table_to_model.items()}

file_model_usage = {}
for path in all_files:
    rel_path = os.path.relpath(path, ".")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    used_models = [m for m in model_names if re.search(r'\b' + m + r'\b', content)]
    if used_models:
        file_model_usage[rel_path] = used_models

print("\nModel usage across backend/app files:")
for fpath, models in sorted(file_model_usage.items()):
    print(f"  {fpath}: {', '.join(models)}")

# Check for raw SQL queries across backend
print("\nRaw SQL searches in backend/app:")
for path in all_files:
    rel_path = os.path.relpath(path, ".")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "exec_driver_sql" in content or "execute(text(" in content or "text(" in content:
        lines = [line.strip() for line in content.splitlines() if any(k in line for k in ["text(", "exec_driver_sql", "execute("])]
        print(f"  {rel_path}:")
        for l in lines[:5]:
            print(f"    {l}")

# Check column attribute accesses
# For example: User.email, Trend.category, etc.
print("\nChecking attribute accesses on models across backend:")
attribute_mismatches = []
for path in all_files:
    rel_path = os.path.relpath(path, ".")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    for model_name, table_name in model_to_table.items():
        table_obj = orm_tables[table_name]
        valid_cols = set(table_obj.columns.keys())
        
        # Also include relationships / properties
        # e.g., User: saved_trends
        # Trend: signals, dna, collections, products, retail_signals, forecasts, prophecies, images
        # ImageRecord: dominant_colors, trend
        # TrendSignal: signal_metadata, trend
        # TrendDNA: to_dict, trend
        valid_attrs = set(valid_cols)
        if model_name == "User":
            valid_attrs.add("saved_trends")
        elif model_name == "Trend":
            valid_attrs.update(["signals", "dna", "collections", "products", "retail_signals", "forecasts", "prophecies", "images"])
        elif model_name == "ImageRecord":
            valid_attrs.update(["dominant_colors", "trend"])
        elif model_name == "TrendSignal":
            valid_attrs.update(["signal_metadata", "trend"])
        elif model_name == "TrendDNA":
            valid_attrs.update(["to_dict", "trend"])
        elif model_name == "Collection":
            valid_attrs.add("trend")
        elif model_name == "Product":
            valid_attrs.add("trend")
        elif model_name == "RetailSignal":
            valid_attrs.add("trend")
        elif model_name == "Forecast":
            valid_attrs.add("trend")
        elif model_name == "Prophecy":
            valid_attrs.add("trend")
        elif model_name == "SavedTrend":
            valid_attrs.update(["user", "trend"])
            
        # Find Model.attr in file
        matches = re.findall(r'\b' + model_name + r'\.([a-zA-Z0-9_]+)\b', content)
        for attr in matches:
            if attr not in valid_attrs:
                # Could be a class method or something
                attribute_mismatches.append((rel_path, model_name, attr))

print(f"Attribute mismatches found: {len(attribute_mismatches)}")
for m in attribute_mismatches:
    print(f"  {m[0]}: {m[1]}.{m[2]} is NOT a known column or relationship on table '{model_to_table[m[1]]}'!")

if not attribute_mismatches:
    print("  ALL attribute accesses on ORM models in backend/app match valid columns and relationships 100%!")
