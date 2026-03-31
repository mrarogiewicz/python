import os
import requests
import pandas as pd
from io import StringIO
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

VALID_API_KEY = os.environ.get("API_KEY")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def scrape_table(url: str) -> list:
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))
    df = tables[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[1] if col[1] else col[0] for col in df.columns]

    df.rename(columns={df.columns[0]: "metric"}, inplace=True)

    return df.to_dict(orient="records")


def check_auth(key: str):
    if not key:
        raise HTTPException(status_code=401, detail="Chýba API kľúč.")
    if key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Nesprávny API kľúč.")


@app.get("/ratios")
def get_ratios(key: str = Query(None), ticker: str = Query("PLTR")):
    check_auth(key)
    try:
        data = scrape_table(f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "data": data}


@app.get("/income")
def get_income(key: str = Query(None), ticker: str = Query("PLTR")):
    check_auth(key)
    try:
        data = scrape_table(f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/?p=quarterly")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "data": data}
