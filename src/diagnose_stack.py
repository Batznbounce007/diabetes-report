#!/usr/bin/env python3
import os
import sys

import requests


def must_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Umgebungsvariable fehlt: {name}")
    return value


def ns_headers(api_secret: str) -> dict:
    headers = {"Accept": "application/json"}
    if api_secret:
        headers["api-secret"] = api_secret
    return headers


def check_nightscout(base_url: str, api_secret: str) -> None:
    print("[1/3] Pruefe Nightscout Status ...")
    status_url = f"{base_url}/api/v1/status.json"
    r = requests.get(status_url, timeout=30)
    r.raise_for_status()
    print(f"  OK: status.json erreichbar ({r.status_code})")

    print("[2/3] Pruefe SGV Zugriff ...")
    entries_url = f"{base_url}/api/v1/entries.json"
    r = requests.get(entries_url, params={"count": 3}, headers=ns_headers(api_secret), timeout=30)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        print(f"  OK: entries.json abrufbar, Datensaetze: {len(data)}")
    else:
        print("  WARNUNG: Unerwartetes Antwortformat in entries.json")


def send_telegram_test(bot_token: str, chat_id: str) -> None:
    print("[3/3] Sende Telegram Testnachricht ...")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "Test: Nightscout/Telegram Verbindung ist aktiv.",
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    print("  OK: Testnachricht gesendet")


def main() -> int:
    try:
        ns_url = must_env("NIGHTSCOUT_URL").rstrip("/")
        ns_secret = os.environ.get("NIGHTSCOUT_API_SECRET", "").strip()
        tg_token = must_env("TELEGRAM_BOT_TOKEN")
        tg_chat = must_env("TELEGRAM_CHAT_ID")

        check_nightscout(ns_url, ns_secret)
        send_telegram_test(tg_token, tg_chat)

        print("\nAlles erfolgreich. Dein Stack ist bereit.")
        return 0
    except Exception as exc:
        print(f"\nFEHLER: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
