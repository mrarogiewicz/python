# import os
# import yfinance as yf
# from fastapi import FastAPI, HTTPException, Query

# app = FastAPI()

# VALID_API_KEY = os.environ.get("API_KEY")


# @app.get("/")
# def get_pe(key: str = Query(None), ticker: str = Query("PLTR")):
#     if not key:
#         raise HTTPException(status_code=401, detail="Chýba API kľúč.")
#     if key != VALID_API_KEY:
#         raise HTTPException(status_code=403, detail="Nesprávny API kľúč.")

#     stock = yf.Ticker(ticker)
#     info = stock.info

#     pe = info.get("trailingPE") or info.get("forwardPE")

#     if pe is None:
#         raise HTTPException(status_code=404, detail=f"P/E ratio pre {ticker} nie je dostupné.")

#     return {
#         "ticker": ticker.upper(),
#         "trailingPE": info.get("trailingPE"),
#         "forwardPE": info.get("forwardPE"),
#     }

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


def get_pe_ratios(ticker: str) -> dict:
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/"

    response = requests.get(url, headers=HEADERS, timeout=15)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' nebol nájdený.")
    response.raise_for_status()

    tables = pd.read_html(response.text)
    if not tables:
        raise HTTPException(status_code=500, detail="Na stránke sa nenašli žiadne tabuľky.")

    df = tables[0]

    # Prvý stĺpec je názov riadku — nastav ho ako index
    df = df.set_index(df.columns[0])

    # Nájdi riadok s PE Ratio (môže sa volať rôzne)
    pe_row = None
    for idx in df.index:
        if "PE Ratio" in str(idx) or "P/E" in str(idx):
            pe_row = idx
            break

    if pe_row is None:
        raise HTTPException(status_code=500, detail="P/E Ratio riadok nebol nájdený v tabuľke.")

    pe_series = df.loc[pe_row]

    # Vyčisti dáta — odstráň prázdne a "-" hodnoty
    result = {}
    for col, val in pe_series.items():
        col_str = str(col).strip()
        val_str = str(val).strip()
        if val_str in ("-", "", "nan", "None"):
            continue
        try:
            result[col_str] = float(val_str.replace(",", ""))
        except ValueError:
            result[col_str] = val_str

    return result


@app.get("/pe")
def get_pe(key: str = Query(None), ticker: str = Query("PLTR")):
    if not key:
        raise HTTPException(status_code=401, detail="Chýba API kľúč.")
    if key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Nesprávny API kľúč.")

    pe_data = get_pe_ratios(ticker)

    return {
        "ticker": ticker.upper(),
        "metric": "PE Ratio",
        "data": pe_data
    }