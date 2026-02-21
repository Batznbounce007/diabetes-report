# T1D Daily Report (Nightscout -> Telegram)

Automatischer Tagesreport aus Nightscout-Daten mit Analyse und Telegram-Versand.

## Schnellstart

1. Nightscout aufsetzen (Render + MongoDB + Glooko Connect):
- `/Users/macbookair/Desktop/Codex_Diabetes/docs/NIGHTSCOUT_SETUP_DE.md`
2. Secrets in GitHub setzen (siehe unten)
3. Workflow `Daily Diabetes Report` manuell starten

## Projektdateien

- Report-Script: `/Users/macbookair/Desktop/Codex_Diabetes/src/daily_report.py`
- Diagnose-Script: `/Users/macbookair/Desktop/Codex_Diabetes/src/diagnose_stack.py`
- Workflow: `/Users/macbookair/Desktop/Codex_Diabetes/.github/workflows/daily_report.yml`

## GitHub Secrets

- `NIGHTSCOUT_URL`
- `NIGHTSCOUT_API_SECRET` (optional, je nach Nightscout-Konfiguration)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TZ` (z. B. `Europe/Berlin`)

## Lokal testen

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# danach eigene Werte setzen
export NIGHTSCOUT_URL="https://dein-nightscout.example.com"
export NIGHTSCOUT_API_SECRET="dein_api_secret"
export TELEGRAM_BOT_TOKEN="dein_bot_token"
export TELEGRAM_CHAT_ID="deine_chat_id"
export TZ="Europe/Berlin"

python3 src/diagnose_stack.py
python3 src/daily_report.py
```

## Hinweis

Die Auswertung liefert strukturierte Hinweise, ersetzt aber keine medizinische Therapieentscheidung.
Aenderungen an Insulindosen immer mit deinem Diabetesteam abstimmen.
