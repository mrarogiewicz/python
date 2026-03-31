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


def get_stock_ratios(symbol: str) -> str:
    url = f"https://stockanalysis.com/stocks/{symbol}/financials/ratios/"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))  # fix pre pandas 2.0+
        df = tables[0]
        return df.to_json(orient="records", indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba: {e}")


@app.get("/ratios")
def get_ratios(key: str = Query(None), ticker: str = Query("PLTR")):
    if not key:
        raise HTTPException(status_code=401, detail="Chýba API kľúč.")
    if key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Nesprávny API kľúč.")

    return get_stock_ratios(ticker.lower())
