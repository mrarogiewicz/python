import os
import requests
import pandas as pd
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


def get_financial_data(ticker: str) -> dict:
    import re
    import json

    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/"

    response = requests.get(url, headers=HEADERS, timeout=15)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' nebol nájdený.")
    response.raise_for_status()

    match = re.search(r'"financialData"\s*:\s*(\{.*?"totalreturn":\[.*?\]\})', response.text, re.DOTALL)
    if not match:
        raise HTTPException(status_code=500, detail="financialData JSON nebol nájdený v stránke.")

    financial_data = json.loads(match.group(1))
    date_keys = financial_data.get("datekey", [])

    # Zostav výsledok: každý riadok = jeden rok, stĺpce = všetky metriky
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