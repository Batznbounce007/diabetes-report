# Nightscout Setup fuer Anfaenger (iOS + CamAPS FX + Libre 3 + Deutschland)

Dieses Dokument fuehrt dich von 0 bis lauffaehig.
Zielbild:

1. CamAPS FX synchronisiert nach Glooko
2. Nightscout zieht Daten ueber `CONNECT_SOURCE=glooko`
3. Telegram-Report laeuft taeglich per GitHub Actions

## Was ich fuer dich bereits gebaut habe

- Report-Script: `/Users/macbookair/Desktop/Codex_Diabetes/src/daily_report.py`
- GitHub Workflow: `/Users/macbookair/Desktop/Codex_Diabetes/.github/workflows/daily_report.yml`
- Diagnose-Script: `/Users/macbookair/Desktop/Codex_Diabetes/src/diagnose_stack.py`

## Schritt 1: Konten anlegen (einmalig)

Du brauchst:

- GitHub Account
- Render Account
- MongoDB Atlas Account
- Telegram Bot Token (hast du schon teilweise)
- Nightscout URL (kommt in Schritt 4)

## Schritt 2: MongoDB Atlas vorbereiten

1. Gehe zu https://www.mongodb.com/atlas
2. Erstelle ein kostenloses Cluster (M0 reicht fuer Start).
3. Unter `Database Access`:
- neuen User erstellen (Username + Password speichern)
4. Unter `Network Access`:
- fuer den Start `0.0.0.0/0` erlauben (spaeter einschranken)
5. Unter `Clusters` -> `Connect` -> `Drivers`:
- Connection String kopieren
- Platzhalter mit deinem DB-User/Passwort ersetzen

Du brauchst am Ende eine `MONGODB_URI`, z. B.:

`mongodb+srv://USER:PASS@cluster0.xyz.mongodb.net/nightscout?retryWrites=true&w=majority`

## Schritt 3: Nightscout Code nach GitHub

1. Neues Repo auf GitHub erstellen, z. B. `nightscout-app`
2. Nightscout-Repository in dein Repo importieren oder forken:
- https://github.com/nightscout/cgm-remote-monitor

Hinweis: Fuer Einsteiger ist Fork + Deploy oft am einfachsten.

## Schritt 4: Nightscout auf Render deployen

1. Gehe zu https://render.com
2. `New` -> `Web Service`
3. GitHub Repo mit Nightscout auswaehlen
4. Build/Start bei Render sind meist auto-erkannt; falls noetig:
- Build Command: `npm install`
- Start Command: `npm start`
5. Environment Variables setzen (sehr wichtig):

Pflichtwerte:
- `MONGODB_URI` = aus Schritt 2
- `API_SECRET` = langes eigenes Passwort (mind. 12-16 Zeichen)
- `TZ` = `Europe/Berlin`
- `DISPLAY_UNITS` = `mg/dl`
- `ENABLE` = `careportal,boluscalc,profile,food,bgstorage,connect`
- `CONNECT_SOURCE` = `glooko`
- `CONNECT_GLOOKO_EMAIL` = deine Glooko-Mail
- `CONNECT_GLOOKO_PASSWORD` = dein Glooko-Passwort

Optional spaeter:
- `AUTH_DEFAULT_ROLES` = je nach gewuenschtem Zugriff

6. Deploy starten und URL notieren, z. B. `https://dein-nightscout.onrender.com`

## Schritt 5: Ersttest Nightscout

Im Browser testen:

- `https://DEINE_URL/api/v1/status.json`
- `https://DEINE_URL/api/v1/entries.json?count=3`

Wenn Daten noch leer sind: 10-30 Minuten warten, dann erneut pruefen.

## Schritt 6: Telegram komplett machen

1. Sende eine Nachricht an `@Diabetescoach_bot`
2. Im Browser:
- `https://api.telegram.org/bot<DEIN_BOT_TOKEN>/getUpdates`
3. `chat.id` kopieren

## Schritt 7: Report-Repo auf GitHub bringen

Dieses Repo hier (`Codex_Diabetes`) nach GitHub pushen.

Danach in diesem Repo unter `Settings -> Secrets and variables -> Actions` folgende Secrets setzen:

- `NIGHTSCOUT_URL` = deine Render-URL
- `NIGHTSCOUT_API_SECRET` = dein API_SECRET aus Nightscout
- `TELEGRAM_BOT_TOKEN` = dein Bot-Token
- `TELEGRAM_CHAT_ID` = chat.id
- `TZ` = `Europe/Berlin`

## Schritt 8: Verbindung mit Diagnose-Script testen

Lokal im Repo ausfuehren:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export NIGHTSCOUT_URL="https://dein-nightscout.onrender.com"
export NIGHTSCOUT_API_SECRET="dein_api_secret"
export TELEGRAM_BOT_TOKEN="dein_bot_token"
export TELEGRAM_CHAT_ID="deine_chat_id"
python3 src/diagnose_stack.py
```

Erwartung:
- Nightscout erreichbar
- SGV Abfrage ok
- Telegram Testnachricht gesendet

## Schritt 9: Daily Workflow starten

In GitHub Actions:
- Workflow `Daily Diabetes Report` manuell starten (`Run workflow`)
- Eingang im Telegram-Chat pruefen

## Troubleshooting (haeufig)

- 401 bei Nightscout: falscher `NIGHTSCOUT_API_SECRET`
- 403/404 bei Render: URL falsch oder Deployment fehlgeschlagen
- Keine Werte in `entries.json`: Glooko-Connect noch nicht synchronisiert
- Telegram 400: `chat_id` falsch oder Bot hat noch keine Nachricht von dir erhalten

## Sicherheit

- Zugangsdaten nur als Secrets speichern, nie im Code.
- Empfehlungen im Report sind nur Entscheidungsunterstuetzung.
- Therapie-/Dosisanpassungen immer mit Diabetesteam abstimmen.
