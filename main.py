import os
import re
import json
import requests
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

VALID_API_KEY = os.environ.get("API_KEY")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}


def js_to_json(js_str: str) -> str:
    """Konvertuje JS objekt (bez úvodzoviek) na validný JSON."""
    # Pridaj úvodzovky okolo unquoted kľúčov napr. datekey: -> "datekey":
    js_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', js_str)
    # Nahraď JavaScript void 0 za null
    js_str = js_str.replace("void 0", "null")
    # Nahraď undefined za null
    js_str = js_str.replace("undefined", "null")
    # Nahraď true/false (už sú lowercase, JSON ich akceptuje)
    return js_str


def extract_js_object(text: str, key: str) -> str:
    """Vyextrahuje JS objekt pre daný kľúč pomocou počítania zátvoriek."""
    pattern = rf'{re.escape(key)}\s*:\s*\{{'
    m = re.search(pattern, text)
    if not m:
        return None

    start = m.end() - 1  # pozícia '{'
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None


def get_financial_data(ticker: str) -> list:
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/"

    response = requests.get(url, headers=HEADERS, timeout=15)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' nebol nájdený.")
    response.raise_for_status()

    html = response.text

    js_obj = extract_js_object(html, "financialData")
    if not js_obj:
        raise HTTPException(status_code=500, detail="financialData objekt sa nenašiel v HTML.")

    try:
        json_str = js_to_json(js_obj)
        financial_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON decode error: {e}. Snippet: {js_obj[:300]}")

    date_keys = financial_data.get("datekey", [])
    if not date_keys:
        raise HTTPException(status_code=500, detail="datekey nie je v dátach.")

    result = []
    for i, date in enumerate(date_keys):
        row = {"period": str(date)}
        for metric, values in financial_data.items():
            if metric == "datekey":
                continue
            if isinstance(values, list) and i < len(values):
                val = values[i]
                row[metric] = round(val, 4) if isinstance(val, float) else val
        result.append(row)

    return result


@app.get("/ratios")
def get_ratios(key: str = Query(None), ticker: str = Query("PLTR")):
    if not key:
        raise HTTPException(status_code=401, detail="Chýba API kľúč.")
    if key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Nesprávny API kľúč.")

    data = get_financial_data(ticker)
    return {
        "ticker": ticker.upper(),
        "data": data
    }
