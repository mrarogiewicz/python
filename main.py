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


def get_financial_data(ticker: str) -> list:
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/"

    response = requests.get(url, headers=HEADERS, timeout=15)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' nebol nájdený.")
    response.raise_for_status()

    html = response.text

    # Pokus 1: štandardný pattern s totalreturn
    match = re.search(r'"financialData"\s*:\s*(\{.*?"totalreturn":\[.*?\]\})', html, re.DOTALL)

    # Pokus 2: všetko medzi financialData a "map"
    if not match:
        match = re.search(r'"financialData"\s*:\s*(\{.*?)\s*,\s*"map"\s*:', html, re.DOTALL)

    # Pokus 3: všetko medzi financialData a "full_count"
    if not match:
        match = re.search(r'"financialData"\s*:\s*(\{.*?)\s*,\s*"full_count"\s*:', html, re.DOTALL)

    if not match:
        # Debug — vráť časť HTML kde by mali byť dáta
        snippet = html[html.find("financialData"):html.find("financialData") + 200] if "financialData" in html else "financialData kľúč sa vôbec nenašiel v HTML"
        raise HTTPException(status_code=500, detail=f"Parse zlyhal. Snippet: {snippet}")

    try:
        financial_data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON decode error: {e}")

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
