---
name: asset-intake-agent
description: Extract invoice, contract, and device-list data for fixed-asset intake, build one intake row per item group, and optionally drive the browser form up to manual submit. Use when the user wants Codex to process varying invoice or checklist formats in real time, map untaxed list prices into the asset-entry form, upload invoice attachments, or prepare repeated fixed-asset intake work as a reusable agent.
---

# Asset Intake Agent

Use this skill to turn project files into reviewable intake rows, then fill the fixed-asset form until the user takes over for manual review and submit.

## Workflow

1. Collect the current project files.
   Supported inputs are invoice images or PDFs, contract images or PDFs, and device-list images or PDFs.
2. Prepare structured rows.
   Run `scripts/run_asset_intake.sh prepare <file>` to OCR the current device list and build `intake_rows.json` plus `intake_rows.csv`.
3. Review extraction output before browser work.
   Open `/Users/uian/Documents/Playground/asset_entry/output/intake_rows.csv` and confirm names, models, quantities, gross unit prices, and gross totals.
4. Drive the form only after review.
   Run `scripts/run_asset_intake.sh fill` to launch the browser flow and stop before each submit.
5. Leave manual-only fields untouched unless the user explicitly changes the rule.
   Keep `使用人`, `资产分类`, and `国标分类` for the user.

## Rules

Follow these rules exactly:

- Treat invoice, contract, and device list as the same project unless the user says otherwise.
- Build one intake row per `名称 + 型号`.
- Use gross values (`金额 + 税额`) for `单价(元)` and `原值/总金额`.
- Fill `原值(元)`, `单价(元)`, `净值(元)`, and `经费1(元)` with the same gross amount for each row.
- Use the invoice for `发票号`, `取得日期`, and attachment upload.
- Fill fixed fields as configured in `/Users/uian/Documents/Playground/asset_entry/config/config.yaml`.
- Stop before clicking `提交`. The user reviews and clicks it manually.

## Current Defaults

Read `/Users/uian/Documents/Playground/asset_entry/config/config.yaml` before running the workflow. The current business defaults are:

- `归口 = 国资处`
- `经费项目1 = 其他`
- `使用方向 = 行政`
- Fixed-asset filtering is enabled

## Current YZU System Notes

- Enter the asset system home page first, then click `固定资产入库`.
- The stock-in form opens inside `stockInHSAM.jsf`.
- Verified stable field IDs for direct fill include:
  - `资产名称 -> RF_BAA02`
  - `型号 -> RF_BAA041`
  - `规格 -> RF_BAA04`
  - `数量 -> RF_BAA09`
  - `原值/总金额 -> RF_BAA10`
  - `发票号 -> RF_BAA33`

## References

- Read `references/workflow.md` for the end-to-end operating procedure and current business assumptions.
- Use `scripts/run_asset_intake.sh` instead of calling the underlying scripts manually unless debugging.
