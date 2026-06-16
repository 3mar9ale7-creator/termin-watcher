#!/usr/bin/env python3
"""
Termin Watcher - GitHub Actions version (run once then exit).
نسخة تشخيص: + على 2817، Weiter، تعليم المربعات، OK.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests
from playwright.sync_api import sync_playwright

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
MAIL_TO = os.environ.get("MAIL_TO", "") or GMAIL_USER

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


def send_msg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=30,
        )
    except Exception as e:
        print("Telegram msg error:", e)


def send_email(subject, body, image_path=None):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("email skipped - no GMAIL secrets set")
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = MAIL_TO
        msg.set_content(body)
        if image_path:
            with open(image_path, "rb") as f:
                msg.add_attachment(
                    f.read(), maintype="image", subtype="png", filename="slot.png"
                )
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("email sent")
    except Exception as e:
        print("email error:", e)


def main():
    start = "https://terminvergabe.muelheim-ruhr.de/select2?md=9"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(locale="de-DE").new_page()

        def shot(label):
            page.screenshot(path="dbg.png", full_page=True)
            send_photo("dbg.png", f"📍 {label}\nURL: {page.url}")

        try:
            page.goto(start, wait_until="domcontentloaded", timeout=60000)
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
            page.wait_for_timeout(2000)

            # نافذة المستندات: علّم كل المربعات المرئية
            boxes = page.locator("input[type=checkbox]:visible")
            n = boxes.count()
            for i in range(n):
                try:
                    boxes.nth(i).check(timeout=3000)
                except Exception:
                    try:
                        boxes.nth(i).click(timeout=3000)
                    except Exception:
                        pass
            page.wait_for_timeout(1000)
            shot(f"5- بعد تعليم {n} مربعات")

            # زر OK
            page.get_by_role("button", name="OK").first.click()
            page.wait_for_timeout(2000)
            shot("6- بعد OK")

        except Exception as e:
            try:
                shot(f"فشل: {e}")
            except Exception:
                pass
        finally:
            browser.close()


if __name__ == "__main__":
    main()
