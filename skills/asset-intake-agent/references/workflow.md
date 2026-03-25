# Workflow

## Input Contract

Expect these files when available:

- Invoice image or PDF
- Contract image or PDF
- Device list image or PDF

Treat them as the same project bundle unless the user states a mismatch.

## Extraction Rules

- OCR the device list first.
- Build one intake row per `名称 + 型号`.
- Use gross values (`金额 + 税额`) for `单价(元)` and `原值/总金额`.
- Mirror the same gross amount into `原值(元)`, `单价(元)`, `净值(元)`, and `经费1(元)`.
- Use invoice data for `发票号` and `取得日期`.
- Use list or contract data for `品牌`, `型号`, `规格`, `数量`.

## Form Rules

- Fill configured fixed fields automatically:
  - `归口 = 国资处`
  - `经费项目1 = 其他`
  - `使用方向 = 行政`
- Leave `使用人`, `资产分类`, and `国标分类` for the user.
- Upload invoice attachments through the attachment flow when required.
- Stop before `提交` every time.

## YZU Navigation Notes

- Land on `workstand.jsf` first.
- Click `固定资产入库` from the home page.
- The stock-in form is loaded in frame URL `stockInHSAM.jsf`.
- Verified direct-fill IDs:
  - `RF_BAA02` = `资产名称`
  - `RF_BAA041` = `型号`
  - `RF_BAA04` = `规格`
  - `RF_BAA09` = `数量`
  - `RF_BAA10` = `原值/总金额`
  - `RF_BAA33` = `发票号`

## Runtime Files

- Config: `/Users/uian/Documents/Playground/asset_entry/config/config.yaml`
- OCR output: `/Users/uian/Documents/Playground/asset_entry/output/raw_ocr.txt`
- Parsed rows: `/Users/uian/Documents/Playground/asset_entry/output/intake_rows.json`
- Review CSV: `/Users/uian/Documents/Playground/asset_entry/output/intake_rows.csv`

## Common Failure Modes

- OCR may merge columns on rotated or low-contrast photos. Prefer PDF or straight photos.
- Browser label matching may fail on custom controls. Add selector overrides in the config when that happens.
- Do not trust extracted totals until the CSV is reviewed against the latest list.
