#!/usr/bin/env python3
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


@dataclass
class Config:
    nightscout_url: str
    nightscout_api_secret: str | None
    telegram_bot_token: str
    telegram_chat_id: str
    timezone: str


def load_config() -> Config:
    url = os.environ.get("NIGHTSCOUT_URL", "").strip().rstrip("/")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not url:
        raise ValueError("NIGHTSCOUT_URL fehlt")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN fehlt")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID fehlt")

    return Config(
        nightscout_url=url,
        nightscout_api_secret=os.environ.get("NIGHTSCOUT_API_SECRET", "").strip() or None,
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        timezone=os.environ.get("TZ", "Europe/Berlin").strip(),
    )


def ns_headers(cfg: Config) -> dict:
    headers = {"Accept": "application/json"}
    if cfg.nightscout_api_secret:
        headers["api-secret"] = cfg.nightscout_api_secret
    return headers


def fetch_sgv(cfg: Config, start_ms: int, end_ms: int) -> list[dict]:
    query = {
        "date": {"$gte": start_ms, "$lt": end_ms},
        "type": "sgv",
    }
    params = {
        "find": json.dumps(query),
        "count": "10000",
    }
    url = f"{cfg.nightscout_url}/api/v1/entries.json"
    resp = requests.get(url, params=params, headers=ns_headers(cfg), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [d for d in data if isinstance(d.get("sgv"), (int, float))]


def fetch_treatments(cfg: Config, start_iso: str, end_iso: str) -> list[dict]:
    query = {
        "created_at": {"$gte": start_iso, "$lt": end_iso},
    }
    params = {
        "find": json.dumps(query),
        "count": "5000",
    }
    url = f"{cfg.nightscout_url}/api/v1/treatments.json"
    resp = requests.get(url, params=params, headers=ns_headers(cfg), timeout=30)
    resp.raise_for_status()
    return resp.json()


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return sorted_values[lo]
    frac = rank - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def count_episodes(values: list[float], threshold: float, below: bool) -> int:
    episodes = 0
    in_episode = False
    for v in values:
        cond = v < threshold if below else v > threshold
        if cond and not in_episode:
            episodes += 1
            in_episode = True
        elif not cond:
            in_episode = False
    return episodes


def analyze(values: list[float], treatments: list[dict]) -> tuple[dict, list[str]]:
    n = len(values)
    if n == 0:
        return {}, ["Keine SGV-Daten für den Auswertungstag gefunden."]

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    sd = math.sqrt(variance)
    cv = (sd / mean * 100.0) if mean > 0 else float("nan")

    in_range = [v for v in values if 70 <= v <= 180]
    below = [v for v in values if v < 70]
    above = [v for v in values if v > 180]
    below_54 = [v for v in values if v < 54]
    above_250 = [v for v in values if v > 250]

    sorted_vals = sorted(values)
    p5 = percentile(sorted_vals, 0.05)
    p95 = percentile(sorted_vals, 0.95)

    carbs = 0.0
    bolus = 0.0
    for t in treatments:
        if isinstance(t.get("carbs"), (int, float)):
            carbs += float(t["carbs"])
        if isinstance(t.get("insulin"), (int, float)):
            bolus += float(t["insulin"])

    metrics = {
        "count": n,
        "avg": mean,
        "sd": sd,
        "cv": cv,
        "tir": len(in_range) / n * 100,
        "tbr": len(below) / n * 100,
        "tbr54": len(below_54) / n * 100,
        "tar": len(above) / n * 100,
        "tar250": len(above_250) / n * 100,
        "min": min(values),
        "max": max(values),
        "p5": p5,
        "p95": p95,
        "hypo_episodes": count_episodes(values, 70, below=True),
        "hyper_episodes": count_episodes(values, 180, below=False),
        "carbs": carbs,
        "bolus": bolus,
    }

    recs: list[str] = []
    if metrics["tbr"] > 4:
        recs.append("TBR ist erhöht (>4%). Muster für Unterzuckerungen prüfen (insb. Nacht/aktive Zeiten) und mit Diabetesteam Basal-/Korrekturstrategie besprechen.")
    if metrics["tbr54"] > 1:
        recs.append("Zeit <54 mg/dL ist zu hoch (>1%). Sicherheitsfokus: Hypo-Prävention priorisieren und Alarme/Targets überprüfen.")
    if metrics["cv"] > 36:
        recs.append("Glukose-Variabilität ist erhöht (CV >36%). Fokus auf konsistentere Mahlzeiten-Bolus-Timings und Trigger (Sport, Stress, späte Mahlzeiten).")
    if metrics["tir"] < 70:
        recs.append("TIR liegt unter 70%. Wiederkehrende Tageszeiten mit Hyperglykämie identifizieren und Faktoren in CamAPS-Einstellungen mit dem Behandlungsteam reviewen.")
    if metrics["tar250"] > 5:
        recs.append("Zeit >250 mg/dL ist relevant. Prüfen, ob Mahlzeiten-Ankündigungen/Carb-Schätzungen oder Infusionsset-Wechsel optimiert werden müssen.")
    if not recs:
        recs.append("Werte sind insgesamt stabil. Aktuelles Vorgehen beibehalten und auf konstante Routinen achten.")

    recs.append("Hinweis: Empfehlungen sind keine medizinische Anweisung und ersetzen nicht die Abstimmung mit deinem Diabetesteam.")
    return metrics, recs


def build_message(report_date: datetime, metrics: dict, recs: list[str]) -> str:
    if not metrics:
        return (
            f"Diabetes Tagesreport ({report_date.strftime('%d.%m.%Y')})\n\n"
            "Keine verwertbaren SGV-Daten gefunden."
        )

    lines = [
        f"Diabetes Tagesreport ({report_date.strftime('%d.%m.%Y')})",
        "",
        "Kernmetriken:",
        f"- TIR 70-180: {metrics['tir']:.1f}%",
        f"- TBR <70: {metrics['tbr']:.1f}% (davon <54: {metrics['tbr54']:.1f}%)",
        f"- TAR >180: {metrics['tar']:.1f}% (davon >250: {metrics['tar250']:.1f}%)",
        f"- Mittelwert: {metrics['avg']:.1f} mg/dL",
        f"- SD/CV: {metrics['sd']:.1f} / {metrics['cv']:.1f}%",
        f"- Min/Max: {metrics['min']:.0f}/{metrics['max']:.0f} mg/dL",
        f"- P5/P95: {metrics['p5']:.0f}/{metrics['p95']:.0f} mg/dL",
        f"- Hypo-/Hyper-Episoden: {metrics['hypo_episodes']}/{metrics['hyper_episodes']}",
        f"- KH / Bolus (aus Treatments): {metrics['carbs']:.0f} g / {metrics['bolus']:.1f} U",
        "",
        "Analyse & Empfehlungen:",
    ]
    lines.extend([f"- {r}" for r in recs])
    return "\n".join(lines)


def send_telegram(cfg: Config, text: str) -> None:
    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": cfg.telegram_chat_id,
        "text": text,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()


def run() -> None:
    cfg = load_config()
    tz = ZoneInfo(cfg.timezone)

    now = datetime.now(tz)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=1)
    end = today

    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    start_iso = start.isoformat()
    end_iso = end.isoformat()

    sgv_entries = fetch_sgv(cfg, start_ms, end_ms)
    sgv_values = [float(x["sgv"]) for x in sorted(sgv_entries, key=lambda i: i.get("date", 0))]
    treatments = fetch_treatments(cfg, start_iso, end_iso)

    metrics, recs = analyze(sgv_values, treatments)
    msg = build_message(start, metrics, recs)
    send_telegram(cfg, msg)


if __name__ == "__main__":
    run()
