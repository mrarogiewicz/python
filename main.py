import os
import yfinance as yf
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

VALID_API_KEY = os.environ.get("API_KEY")


@app.get("/")
def get_pe(key: str = Query(None), ticker: str = Query("PLTR")):
    if not key:
        raise HTTPException(status_code=401, detail="Chýba API kľúč.")
    if key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Nesprávny API kľúč.")

    stock = yf.Ticker(ticker)
    info = stock.info

    pe = info.get("trailingPE") or info.get("forwardPE")

    if pe is None:
        raise HTTPException(status_code=404, detail=f"P/E ratio pre {ticker} nie je dostupné.")

    return {
        "ticker": ticker.upper(),
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
    }