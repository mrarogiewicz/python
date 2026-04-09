import os
import requests
import pandas as pd
from io import StringIO
from fastapi import FastAPI, HTTPException, Query, Header

app = FastAPI()

VALID_API_KEY = os.environ.get("API_KEY")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# --- Helpers ---

def check_auth(key: str = None, x_api_key: str = None):
    """Akceptuje API kľúč z URL parametra aj z hlavičky X-Api-Key."""
    provided = x_api_key or key
    if not provided:
        raise HTTPException(status_code=401, detail="Chýba API kľúč.")
    if provided != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Nesprávny API kľúč.")


def scrape_table(url: str) -> list:
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))
    df = tables[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[1] if col[1] else col[0] for col in df.columns]

    df.rename(columns={df.columns[0]: "metric"}, inplace=True)

    return df.to_dict(orient="records")


def build_url(base: str, period: str) -> str:
    if period == "annual":
        return base
    return f"{base}?p=quarterly"


# --- Endpoints ---

@app.get("/keepalive")
def keepalive():
    return "keeping alive..."


@app.get("/ratios")
def get_ratios(
    ticker: str = Query("PLTR"),
    period: str = Query("quarterly"),
    key: str = Query(None),
    x_api_key: str = Header(None),
):
    check_auth(key, x_api_key)
    try:
        url = build_url(f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/", period)
        data = scrape_table(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "period": period, "data": data}


@app.get("/income")
def get_income(
    ticker: str = Query("PLTR"),
    period: str = Query("quarterly"),
    key: str = Query(None),
    x_api_key: str = Header(None),
):
    check_auth(key, x_api_key)
    try:
        url = build_url(f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/", period)
        data = scrape_table(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "period": period, "data": data}


@app.get("/balance")
def get_balance(
    ticker: str = Query("PLTR"),
    period: str = Query("quarterly"),
    key: str = Query(None),
    x_api_key: str = Header(None),
):
    check_auth(key, x_api_key)
    try:
        url = build_url(f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/balance-sheet/", period)
        data = scrape_table(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "period": period, "data": data}


@app.get("/cashflow")
def get_cashflow(
    ticker: str = Query("PLTR"),
    period: str = Query("quarterly"),
    key: str = Query(None),
    x_api_key: str = Header(None),
):
    check_auth(key, x_api_key)
    try:
        url = build_url(f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/cash-flow-statement/", period)
        data = scrape_table(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "period": period, "data": data}
