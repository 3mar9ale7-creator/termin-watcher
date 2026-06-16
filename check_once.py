#!/usr/bin/env python3
"""
Termin Watcher - GitHub Actions version (run once then exit).
Runs automatically every few minutes via GitHub, and sends an alert
(Telegram + email) only when a real appointment is available.
You do the booking manually via the link.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests
from playwright.sync_api import sync_playwright

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
URL = os.environ.get(
    "TERMIN_URL",
    "https://terminvergabe.muelheim-ruhr.de/location?mdt=150&select_cnc=1&cnc-2817=1",
)

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
ERRORS = [
    "kein gültiger mandant",
    "sitzung ist abgelaufen",
    "fehlermeldung",
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
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(locale="de-DE").new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        text = page.inner_text("body").lower()
        reached = any(s in text for s in REACHED)

        if any(s in text for s in ERRORS) and not reached:
            print("error/session page - skip")
        elif any(s in text for s in NO_SLOT):
            print("no slot")
        elif True:
            page.screenshot(path="slot.png", full_page=True)
            caption = (
                "🚨 Es scheint jetzt einen freien Termin zu geben!\n"
                "Schnell buchen:\n" + URL
            )
            send_photo("slot.png", caption)
            send_email("🚨 Termin verfügbar!", caption, "slot.png")
            print("AVAILABLE - notified")
        else:
            print("unknown page state - no message sent")

        browser.close()


if __name__ == "__main__":
    main()
