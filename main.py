import os
import requests
import pandas as pd
import threading
import time
from io import StringIO
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

VALID_API_KEY = os.environ.get("API_KEY")
RENDER_URL = os.environ.get("RENDER_URL")  # napr. https://tvoja-app.onrender.com

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# --- Keep-alive ---

def keep_alive():
    """Pinguje samu seba každých 10 minút aby Render neuspával aplikáciu."""
    while True:
        time.sleep(600)  # 10 minút
        if RENDER_URL:
            try:
                requests.get(f"{RENDER_URL}/ping", timeout=10)
                print("✅ Keep-alive ping odoslaný")
            except Exception as e:
                print(f"⚠️ Keep-alive ping zlyhal: {e}")


@app.on_event("startup")
def startup():
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()


@app.get("/ping")
def ping():
    return {"status": "ok"}


# --- Helpers ---

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


# --- Endpoints ---

@app.get("/ratios")
def get_ratios(key: str = Query(None), ticker: str = Query("PLTR"), period: str = Query("quarterly")):
    check_auth(key)
    try:
        if period == "annual":
            url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/"
        else:
            url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/?p=quarterly"
        data = scrape_table(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "period": period, "data": data}


@app.get("/income")
def get_income(key: str = Query(None), ticker: str = Query("PLTR"), period: str = Query("quarterly")):
    check_auth(key)
    try:
        if period == "annual":
            url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/"
        else:
            url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/?p=quarterly"
        data = scrape_table(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")
    return {"ticker": ticker.upper(), "period": period, "data": data}
