# Asset Entry Assistant

Two modes:
1) OCR + build intake rows (semi-automatic)
2) Browser auto-fill (Playwright) and stop before submit

## 1) OCR + Build Intake Rows

### Install dependencies
- macOS OCR engine: `brew install tesseract`
- Python deps: `pip3 install pyyaml`

### Run OCR + build intake rows
```
./scripts/run_asset_intake.sh prepare /path/to/清单.jpg
```

This writes:
- `output/raw_ocr.txt`
- `output/parsed_items.json`
- `output/intake_rows.json`
- `output/intake_rows.csv`

Review `output/intake_rows.csv`, adjust if needed, then re-export to JSON if you edit.

Business defaults currently in use:
- `归口 = 国资处`
- `使用方向 = 行政`
- `单价(元)` / `原值/总金额` / `经费项目1` all use the same original-price value (`金额数值 + 税额数值`)

## 2) Browser Auto-Fill (Playwright)

### Install dependencies
```
pip3 install playwright pyyaml
playwright install
```

### Configure
Edit `config/config.yaml`:
- `site.url`: the exact intake form URL
- `site.browser_mode`: `persistent` for the current dedicated Playwright profile, or `cdp` to attach to an already-open Chrome session
- `site.startup_action`: `goto`, `preserve`, or `new_tab`; for SSO flows use `cdp + preserve`
- `site.cdp_url`: Chrome DevTools endpoint when `browser_mode: cdp` (default `http://127.0.0.1:9222`)
- Optional: `site.wait_for_ready_selector`
- Optional: `selectors` overrides for fields that fail label matching
- `precise_field_ids`: verified direct-fill IDs for stable fields in the YZU stock-in form
- `site.user_data_dir`: used only in `persistent` mode

### Run
```
./scripts/run_asset_intake.sh fill
```

The script pauses for manual review before each submit.

### Browser session reuse modes

`persistent` mode:
- Current default.
- Playwright launches its own persistent Chrome profile under `tmp/chrome_profile`.
- Safer for repeatable automation, but login state lives in that dedicated profile.

`cdp` mode:
- Reuses an already running Chrome session, which is the part worth borrowing from `opencli`.
- Useful when you want to keep your normal logged-in browser state instead of maintaining a second profile.
- For SSO systems, set `site.startup_action: preserve` so the script does not jump back to the asset system's native login URL.
- Start Chrome with remote debugging enabled, then set `site.browser_mode: cdp`.

Example on macOS:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

## Notes
- Amounts use the same original-price value (`金额数值 + 税额数值`) for `单价(元)`, `原值/总金额`, and `经费项目1` in the current YZU flow.
- Submit is always manual.
- Different list templates may need edits to `field_map` or `selectors`.
- The YZU stock-in form is opened from the asset home page via `固定资产入库`, and the form lives in `stockInHSAM.jsf`.
