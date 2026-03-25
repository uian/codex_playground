#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

COLUMNS_GUESS = ["名称", "品牌", "型号", "数量", "单位", "单价", "总价", "备注"]


def run(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_tesseract():
    if shutil.which("tesseract") is None:
        print("tesseract not found. Install via: brew install tesseract", file=sys.stderr)
        sys.exit(2)


def pdf_to_images(pdf_path: Path, out_dir: Path):
    # Try pdftoppm if available
    if shutil.which("pdftoppm") is None:
        print("pdftoppm not found. Please provide images or install poppler.", file=sys.stderr)
        sys.exit(3)
    out_prefix = out_dir / "page"
    cmd = ["pdftoppm", "-r", "200", "-jpeg", str(pdf_path), str(out_prefix)]
    code, _, err = run(cmd)
    if code != 0:
        print(err, file=sys.stderr)
        sys.exit(code)
    return sorted(out_dir.glob("page-*.jpg"))


def ocr_image(img_path: Path):
    cmd = [
        "tesseract",
        str(img_path),
        "stdout",
        "-l",
        "chi_sim+eng",
        "--psm",
        "6",
    ]
    code, out, err = run(cmd)
    if code != 0:
        print(err, file=sys.stderr)
        sys.exit(code)
    return out


def parse_rows(text: str):
    # Heuristic: find lines with at least two numeric fields
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(re.findall(r"\d", line)) < 2:
            continue
        # split by 2+ spaces
        parts = re.split(r"\s{2,}", line)
        if len(parts) < 3:
            continue
        rows.append(parts)
    # map to columns guess
    items = []
    for parts in rows:
        item = {}
        for i, col in enumerate(COLUMNS_GUESS):
            if i < len(parts):
                item[col] = parts[i]
        # clean numeric fields
        for k in ["数量", "单价", "总价"]:
            if k in item:
                item[k] = item[k].replace(",", "").replace("¥", "").strip()
        items.append(item)
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="image or pdf path")
    parser.add_argument("--out", default=str(OUTPUT), help="output dir")
    args = parser.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ensure_tesseract()

    images = []
    if in_path.suffix.lower() == ".pdf":
        tmp_dir = out_dir / "_pdf_pages"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        images = pdf_to_images(in_path, tmp_dir)
    else:
        images = [in_path]

    all_text = []
    for img in images:
        all_text.append(ocr_image(img))

    raw_text = "\n\n".join(all_text)
    raw_path = out_dir / "raw_ocr.txt"
    raw_path.write_text(raw_text, encoding="utf-8")

    items = parse_rows(raw_text)
    parsed_path = out_dir / "parsed_items.json"
    parsed_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {raw_path}")
    print(f"Wrote {parsed_path}")


if __name__ == "__main__":
    main()
