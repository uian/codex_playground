#!/usr/bin/env python3
import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "config.yaml"
OUTPUT = ROOT / "output"


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML not installed. Run: pip3 install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def to_number(value):
    try:
        return float(str(value).replace(",", "").replace("¥", "").strip())
    except Exception:
        return None


def to_decimal(value):
    text = str(value).replace(",", "").replace("¥", "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def format_decimal(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.01"))
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def normalize_item(item):
    out = dict(item)
    for k in ["数量", "单价", "总价"]:
        if k in out and out[k] is not None:
            out[k] = str(out[k]).replace(",", "").replace("¥", "").strip()
    return out


def group_items(items, group_keys):
    grouped = {}
    for item in items:
        key = tuple((item.get(k, "") or "").strip() for k in group_keys)
        grouped.setdefault(key, []).append(item)
    return grouped


def original_price_value(item, amount_rules):
    source_fields = amount_rules.get("source_fields", ["金额数值", "税额数值"])
    total = Decimal("0")
    found = False
    for field in source_fields:
        value = to_decimal(item.get(field))
        if value is None:
            continue
        total += value
        found = True
    if found:
        return format_decimal(total)

    for field in amount_rules.get("fallback_source_fields", ["单价", "总价"]):
        value = to_decimal(item.get(field))
        if value is not None:
            return format_decimal(value)
    return None


def is_fixed_asset(item, rule, amount_rules):
    if not rule or not rule.get("enabled", True):
        return True
    unit_threshold = rule.get("unit_threshold", 1000)
    batch_unit_threshold = rule.get("batch_unit_threshold", 500)
    batch_total_threshold = rule.get("batch_total_threshold", 5000)

    qty = to_number(item.get("数量")) or 0
    original_price = to_number(original_price_value(item, amount_rules)) or 0
    unit = to_number(item.get("单价")) or original_price
    total = to_number(item.get("总价")) or original_price

    if unit >= unit_threshold:
        return True
    if unit >= batch_unit_threshold and total >= batch_total_threshold and qty > 0:
        return True
    return False


def build_rows(items, config):
    fixed = config.get("fixed_fields", {})
    field_map = config.get("field_map", {})
    group_keys = config.get("group_by", ["名称", "型号"])
    rule = config.get("fixed_asset_rule", {})
    amount_rules = config.get("amount_rules", {})

    grouped = group_items(items, group_keys)

    rows = []
    skipped = []
    for key, group in grouped.items():
        # merge by taking first non-empty value for each field
        merged = {}
        for item in group:
            for k, v in item.items():
                if v is None or str(v).strip() == "":
                    continue
                merged.setdefault(k, v)

        if not is_fixed_asset(merged, rule, amount_rules):
            skipped.append(merged)
            continue

        row = {}
        # fixed fields
        for k, v in fixed.items():
            row[k] = v
        # mapped fields
        for src, dst in field_map.items():
            if src in merged:
                row[dst] = merged[src]

        amount_value = original_price_value(merged, amount_rules)
        if amount_value is not None:
            for field in amount_rules.get("target_fields", ["单价(元)", "原值/总金额", "经费项目1"]):
                row[field] = amount_value
        rows.append(row)

    return rows, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="parsed_items.json from ocr_extract.py")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--out", default=str(OUTPUT))
    args = parser.parse_args()

    config = load_yaml(Path(args.config))
    items = json.loads(Path(args.input).read_text(encoding="utf-8"))
    items = [normalize_item(i) for i in items]

    rows, skipped = build_rows(items, config)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "intake_rows.json"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV for manual review/editing
    if rows:
        csv_path = out_dir / "intake_rows.csv"
        headers = sorted({k for r in rows for k in r.keys()})
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {csv_path}")

    if skipped:
        skipped_path = out_dir / "skipped_items.json"
        skipped_path.write_text(json.dumps(skipped, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {skipped_path}")

    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
