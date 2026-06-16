#!/usr/bin/env python3
"""
Termin Watcher - GitHub Actions version (run once then exit).
يمر بالخطوات ويفحص المواعيد ويرسل تنبيه تيليجرام عند التوفّر.
"""
import os

import requests
from playwright.sync_api import sync_playwright

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

START = "https://terminvergabe.muelheim-ruhr.de/select2?md=9"

NO_SLOT = [
    "keine zeiten verfügbar",
    "kein freier termin verfügbar",
    "leider kein termin verfügbar",
    "ist leider kein termin",
]
REACHED = [
    "terminvorschläge",
    "übersicht zu ihrem termin",
    "schritt 4",
]


def send_photo(path, caption):
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": f},
                timeout=60,
            )
    except Exception as e:
        print("Telegram photo error:", e)
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": caption},
            timeout=30,
        )


def main():
    test_mode = bool(os.getenv("TEST_MODE"))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(locale="de-DE").new_page()
        try:
            page.goto(START, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            try:
                page.get_by_role("button", name="Akzeptieren").click(timeout=5000)
                page.wait_for_timeout(1500)
            except Exception:
                pass

            page.get_by_text(
                "Studierende und Anerkennung der Berufsqualifikation", exact=False
            ).locator("visible=true").first.click()
            page.wait_for_timeout(2000)

            page.locator("#button-plus-2817").click()
            page.wait_for_timeout(1500)

            page.get_by_role("button", name="Weiter").first.click()
            page.wait_for_timeout(2500)

            page.evaluate("""() => {
                const cbs = [...document.querySelectorAll('input.documentlist_item_cb')];
                cbs.forEach(cb => {
                    cb.checked = true;
                    ['mousedown','mouseup','click','change','input'].forEach(ev =>
                        cb.dispatchEvent(new Event(ev, {bubbles: true})));
                    const lbl = cb.parentElement.querySelector('label.required');
                    if (lbl) ['mousedown','mouseup','click'].forEach(ev =>
                        lbl.dispatchEvent(new Event(ev, {bubbles: true})));
                });
            }""")
            page.wait_for_timeout(1500)

            page.evaluate("""() => {
                const ok = document.querySelector('#OKButton');
                if (ok) {
                    ok.removeAttribute('disabled');
                    ok.removeAttribute('aria-disabled');
                    ok.classList.remove('disabledButton');
                    ok.click();
                }
            }""")
            page.wait_for_timeout(2500)

            page.get_by_role("button", name="Weiter").first.click()
            page.wait_for_url("**/suggest", timeout=30000)
            page.wait_for_timeout(2500)

            text = page.inner_text("body").lower()
            reached = "/suggest" in page.url and any(s in text for s in REACHED)
            has_slot = reached and not any(s in text for s in NO_SLOT)

            if has_slot or test_mode:
                page.screenshot(path="slot.png", full_page=True)
                if test_mode and not has_slot:
                    caption = "✅ TEST: التنبيه يعمل (لا يوجد موعد فعلي الآن)"
                else:
                    caption = (
                        "🚨 Termin verfügbar in Mülheim!\n"
                        "Schnell buchen:\n" + START
                    )
                send_photo("slot.png", caption)
                print("notified")
            else:
                print("no slot")

        except Exception as e:
            try:
                page.screenshot(path="debug.png", full_page=True)
                send_photo("debug.png", f"⚠️ فشل: {e}")
            except Exception:
                pass
        finally:
            browser.close()


if __name__ == "__main__":
    main()
