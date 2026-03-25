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


def load_config(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def summarize_frame(frame, max_text=1200):
    body = frame.locator("body")
    text = ""
    try:
        text = body.inner_text(timeout=3000)
    except Exception:
        text = ""
    text = " ".join(text.split())[:max_text]

    fields = []
    try:
        locator = frame.locator("input, textarea, select, [role='textbox'], [role='combobox']")
        count = min(locator.count(), 30)
        for i in range(count):
            el = locator.nth(i)
            try:
                fields.append(
                    {
                        "tag": el.evaluate("e => e.tagName.toLowerCase()"),
                        "type": el.get_attribute("type"),
                        "name": el.get_attribute("name"),
                        "id": el.get_attribute("id"),
                        "placeholder": el.get_attribute("placeholder"),
                        "aria_label": el.get_attribute("aria-label"),
                    }
                )
            except Exception:
                continue
    except Exception:
        pass

    return {"url": frame.url, "text": text, "fields": fields}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    user_data_dir = config.get("site", {}).get("user_data_dir", str(ROOT / "tmp" / "chrome_profile"))

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=args.headless,
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.goto("about:blank")
        print("请在打开的受控浏览器中进入目标页面，然后回到终端按回车开始探测。")
        input()

        report = []
        for i, pg in enumerate(context.pages):
            page_info = {
                "index": i,
                "url": pg.url,
                "title": "",
                "frames": [],
            }
            try:
                page_info["title"] = pg.title()
            except Exception:
                pass
            for j, frame in enumerate(pg.frames):
                frame_info = summarize_frame(frame)
                frame_info["index"] = j
                page_info["frames"].append(frame_info)
            report.append(page_info)

        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("探测完成。按回车关闭浏览器。")
        input()
        context.close()


if __name__ == "__main__":
    main()
