#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML not installed in the selected Python environment.")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("Playwright not installed in the selected Python environment.")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "config.yaml"
DEFAULT_INPUT = ROOT / "output" / "intake_rows.json"


def load_config(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def create_browser_context(playwright, site):
    browser_mode = site.get("browser_mode", "persistent")

    if browser_mode == "cdp":
        cdp_url = site.get("cdp_url", "http://127.0.0.1:9222")
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = browser.new_context(viewport={"width": 1400, "height": 900})
        return browser, context

    user_data_dir = site.get("user_data_dir", str(ROOT / "tmp" / "chrome_profile"))
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        viewport={"width": 1400, "height": 900},
    )
    return None, context


def iter_targets(context):
    for page in context.pages:
        yield ("page", page)
        for frame in page.frames:
            yield ("frame", frame)


def list_tabs(context):
    for i, page in enumerate(context.pages):
        try:
            title = page.title()
        except Exception:
            title = ""
        print(f"[{i}] {title} | {page.url}")


def click_text(target, text):
    selectors = [
        f"text={text}",
        f"xpath=//*[contains(normalize-space(.), '{text}')]",
    ]
    for selector in selectors:
        locator = target.locator(selector)
        count = min(locator.count(), 20)
        for i in range(count):
            el = locator.nth(i)
            try:
                if el.is_visible():
                    el.click(timeout=2000)
                    return True
            except Exception:
                continue
    return False


def click_anywhere(context, text):
    for kind, target in iter_targets(context):
        try:
            if click_text(target, text):
                print(f"clicked {text} in {kind}")
                return True
        except Exception:
            continue
    print(f"not found: {text}")
    return False


def inspect(context, limit=800):
    for i, page in enumerate(context.pages):
        try:
            title = page.title()
        except Exception:
            title = ""
        print(f"PAGE[{i}] {title} | {page.url}")
        for j, frame in enumerate(page.frames):
            try:
                text = frame.locator("body").inner_text(timeout=2000)
            except Exception:
                text = ""
            text = " ".join(text.split())[:limit]
            print(f"  FRAME[{j}] {frame.url}")
            print(f"  TEXT: {text}")


def fields(context, limit=40):
    for i, page in enumerate(context.pages):
        print(f"PAGE[{i}] {page.url}")
        for j, frame in enumerate(page.frames):
            print(f"  FRAME[{j}] {frame.url}")
            try:
                locator = frame.locator("input, textarea, select")
                count = min(locator.count(), limit)
            except Exception:
                count = 0
            for k in range(count):
                el = locator.nth(k)
                try:
                    tag = el.evaluate("e => e.tagName.toLowerCase()")
                except Exception:
                    tag = ""
                try:
                    type_ = el.get_attribute("type")
                except Exception:
                    type_ = ""
                try:
                    name = el.get_attribute("name")
                except Exception:
                    name = ""
                try:
                    id_ = el.get_attribute("id")
                except Exception:
                    id_ = ""
                try:
                    placeholder = el.get_attribute("placeholder")
                except Exception:
                    placeholder = ""
                print(
                    f"    [{k}] tag={tag} type={type_} name={name} id={id_} placeholder={placeholder}"
                )


def target_stockin_frame(context):
    for page in context.pages:
        for frame in page.frames:
            if "stockInHSAM.jsf" in frame.url:
                return frame
    return None


def set_field_by_id(frame, field_id, value):
    locator = frame.locator(f"#{field_id}")
    if locator.count() == 0:
        print(f"miss id: {field_id}")
        return False
    el = locator.first
    try:
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            el.select_option(label=str(value))
        else:
            el.fill(str(value))
        print(f"ok id: {field_id} = {value}")
        return True
    except Exception as e:
        print(f"fail id: {field_id} = {value} | {e}")
        return False


def fill_precise_first_row(context, row):
    frame = target_stockin_frame(context)
    if not frame:
        print("stock-in frame not found")
        return

    field_map = {
        "资产名称": "RF_BAA02",
        "型号": "RF_BAA041",
        "规格": "RF_BAA04",
        "数量": "RF_BAA09",
        "原值/总金额": "RF_BAA10",
        "发票号": "RF_BAA33",
        "取得日期": "RF_BAA21",
        "供应商": "RF_BAA31",
    }

    for key, field_id in field_map.items():
        value = row.get(key)
        if value is None:
            continue
        set_field_by_id(frame, field_id, value)


def fill_by_label(target, label, value):
    label_locator = target.locator(
        f"xpath=//*[self::td or self::th or self::label or self::span or self::div][contains(normalize-space(.), '{label}')][1]"
    )
    if label_locator.count() == 0:
        return False

    row = label_locator.first.locator("xpath=ancestor::*[self::tr or self::div or self::li][1]")
    candidates = row.locator("input, textarea, select")
    if candidates.count() == 0:
        return False

    for i in range(candidates.count()):
        el = candidates.nth(i)
        try:
            if not el.is_visible() or not el.is_enabled():
                continue
            tag = el.evaluate("e => e.tagName.toLowerCase()")
            if tag == "select":
                el.select_option(label=str(value))
            else:
                el.fill(str(value))
            return True
        except Exception:
            continue
    return False


def fill_first_row(context, row):
    for label, value in row.items():
        ok = False
        for _, target in iter_targets(context):
            try:
                if fill_by_label(target, label, value):
                    ok = True
                    break
            except Exception:
                continue
        print(f"{'ok' if ok else 'miss'}: {label} = {value}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    args = parser.parse_args()

    config = load_config(Path(args.config))
    rows = load_rows(Path(args.input))
    site = config.get("site", {})

    with sync_playwright() as p:
        browser, context = create_browser_context(p, site)
        if not context.pages:
            page = context.new_page()
            page.goto("about:blank")

        print("controller ready")
        print("commands: tabs | click <text> | inspect | fields | fill1 | fill_precise1 | open <url> | quit")

        while True:
            try:
                raw = input("> ").strip()
            except EOFError:
                break

            if not raw:
                continue
            if raw == "quit":
                break
            if raw == "tabs":
                list_tabs(context)
                continue
            if raw.startswith("open "):
                url = raw[5:].strip()
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url)
                print(f"opened {url}")
                continue
            if raw.startswith("click "):
                click_anywhere(context, raw[6:].strip())
                continue
            if raw == "inspect":
                inspect(context)
                continue
            if raw == "fields":
                fields(context)
                continue
            if raw == "fill1":
                fill_first_row(context, rows[0])
                continue
            if raw == "fill_precise1":
                fill_precise_first_row(context, rows[0])
                continue
            print("unknown command")

        context.close()
        if browser:
            browser.close()


if __name__ == "__main__":
    main()
