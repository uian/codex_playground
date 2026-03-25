#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML not installed. Run: pip3 install pyyaml")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("Playwright not installed. Run: pip3 install playwright && playwright install")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "config.yaml"
DEFAULT_INPUT = ROOT / "output" / "intake_rows.json"


def load_config(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def create_browser_context(playwright, site, headless):
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
        headless=headless,
        viewport={"width": 1400, "height": 900},
    )
    return None, context


def pick_active_page(context):
    if context.pages:
        return context.pages[-1]
    return context.new_page()


def prepare_start_page(context, site):
    browser_mode = site.get("browser_mode", "persistent")
    startup_action = site.get("startup_action")
    url = site.get("url", "")

    if startup_action is None:
        startup_action = "preserve" if browser_mode == "cdp" else "goto"

    page = pick_active_page(context)

    if startup_action == "goto":
        if not url:
            raise SystemExit("config.site.url is empty. Please set the form page URL.")
        page.goto(url)
    elif startup_action == "new_tab":
        page = context.new_page()
        if url:
            page.goto(url)
    elif startup_action == "preserve":
        pass
    else:
        raise SystemExit(
            f"Unsupported config.site.startup_action: {startup_action}. Use goto, new_tab, or preserve."
        )

    return page


def click_text_in_context(page, text):
    candidates = [
        f"text={text}",
        f"xpath=//*[self::a or self::button or self::span or self::div][contains(normalize-space(.), '{text}')]",
    ]

    for locator_str in candidates:
        locator = page.locator(locator_str)
        count = min(locator.count(), 20)
        for i in range(count):
            el = locator.nth(i)
            try:
                if el.is_visible():
                    el.click(timeout=3000)
                    return True
            except Exception:
                continue
    return False


def click_text_anywhere(context, text):
    for page in context.pages:
        try:
            if click_text_in_context(page, text):
                return True
        except Exception:
            pass
        for frame in page.frames:
            try:
                if click_text_in_context(frame, text):
                    return True
            except Exception:
                continue
    return False


def target_stockin_frame(context):
    for page in context.pages:
        for frame in page.frames:
            if "stockInHSAM.jsf" in frame.url:
                return frame
    return None


def set_field_by_id(frame, field_id, value):
    locator = frame.locator(f"#{field_id}")
    if locator.count() == 0:
        return False
    el = locator.first
    try:
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            el.select_option(label=str(value))
        else:
            el.fill(str(value))
        return True
    except Exception:
        return False


def fill_by_label(page, label, value, selectors):
    # Selector override
    if label in selectors:
        page.locator(selectors[label]).first.fill(str(value))
        return True

    # Try to find label text in table cells or spans
    label_locator = page.locator(
        f"xpath=//*[self::td or self::th or self::label or self::span][contains(normalize-space(.), '{label}')][1]"
    )
    if label_locator.count() == 0:
        return False

    # Use the first match
    label_el = label_locator.first
    row = label_el.locator("xpath=ancestor::tr[1]")
    if row.count() == 0:
        return False

    # Try inputs/selects/textarea within the row
    candidates = row.locator("input, textarea, select")
    if candidates.count() == 0:
        return False

    # Pick the first visible and enabled candidate
    for i in range(candidates.count()):
        el = candidates.nth(i)
        if el.is_visible() and el.is_enabled():
            tag = el.evaluate("e => e.tagName.toLowerCase()")
            if tag == "select":
                el.select_option(label=str(value))
            else:
                el.fill(str(value))
            return True
    return False


def fill_by_label_anywhere(context, label, value, selectors):
    for page in context.pages:
        try:
            if fill_by_label(page, label, value, selectors):
                return True
        except Exception:
            pass
        for frame in page.frames:
            try:
                if fill_by_label(frame, label, value, selectors):
                    return True
            except Exception:
                continue
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--pause-before-submit", action="store_true", default=True)
    args = parser.parse_args()

    config = load_config(Path(args.config))
    rows = load_rows(Path(args.input))

    site = config.get("site", {})
    wait_selector = site.get("wait_for_ready_selector", "")
    selectors = config.get("selectors", {})
    post_login_click_labels = site.get("post_login_click_labels", [])
    precise_field_ids = config.get("precise_field_ids", {})

    with sync_playwright() as p:
        browser, context = create_browser_context(p, site, args.headless)
        page = prepare_start_page(context, site)

        # In SSO/CDP flows we keep the current tab and let the user confirm the target page is ready.
        print("Please confirm the correct intake page is open in the browser. Press Enter here when ready...")
        input()

        for label in post_login_click_labels:
            print(f"Trying to click: {label}")
            ok = click_text_anywhere(context, label)
            if not ok:
                print(f"WARN: Could not click navigation label: {label}")
            else:
                time.sleep(2)

        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=120000)

        for idx, row in enumerate(rows, start=1):
            print(f"Filling row {idx}/{len(rows)}")

            stockin_frame = target_stockin_frame(context)
            for label, value in row.items():
                if stockin_frame and label in precise_field_ids:
                    ok = set_field_by_id(stockin_frame, precise_field_ids[label], value)
                    if ok:
                        continue
                ok = fill_by_label_anywhere(context, label, value, selectors)
                if not ok:
                    print(f"WARN: Could not locate field for label: {label}")

            # Pause for manual review and submit
            print("Review the form. Submit manually if approved.")
            input("Press Enter to continue to next item...")

        context.close()
        if browser:
            browser.close()


if __name__ == "__main__":
    main()
