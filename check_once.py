#!/usr/bin/env python3
"""
Termin Watcher — نسخة GitHub Actions (فحص واحد ثم خروج).
تُشغَّل تلقائياً كل بضع دقائق عبر GitHub، وترسل رسالة تيليجرام فقط
عند توفّر موعد فعلي. الحجز تقوم به أنت يدوياً عبر الرابط.
"""
import os
import requests
from playwright.sync_api import sync_playwright

TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
URL = os.environ.get(
    "TERMIN_URL",
    "https://terminvergabe.muelheim-ruhr.de/location?mdt=150&select_cnc=1&cnc-2817=1",
)

# عبارات تعني "لا توجد مواعيد" (مضبوطة على نص صفحتك الحقيقي)
NO_SLOT = [
    "keine zeiten verfügbar",
    "kein freier termin verfügbar",
    "leider kein termin verfügbar",
    "ist leider kein termin",
]
# عبارات تؤكد أننا وصلنا لصفحة الخطوة ٤ (تظهر في الحالتين)
REACHED = [
    "terminvorschläge",
    "übersicht zu ihrem termin",
    "schritt 4",
]
# صفحات الخطأ التي يجب تجاهلها
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
            print("error/session page — skip")
        elif any(s in text for s in NO_SLOT):
            print("no slot")
        elif reached:
            page.screenshot(path="slot.png", full_page=True)
            send_photo(
                "slot.png",
                "🚨 يبدو أن هناك موعداً شاغراً الآن في مكتب الأجانب!\n"
                "افتح واحجز بسرعة:\n" + URL,
            )
            print("AVAILABLE — notified")
        else:
            print("unknown page state — no message sent")

        browser.close()


if __name__ == "__main__":
    main()
