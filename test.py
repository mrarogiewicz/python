import yfinance as yf
import pandas as pd

def get_valuation_history(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    
    # 1. Získanie finančných výkazov (Kvartálne)
    # Tieto obsahujú: Revenue, Net Income, Debt, Cash atď.
    income_stmt = stock.quarterly_financials
    balance_sheet = stock.quarterly_balance_sheet
    
    if income_stmt.empty or balance_sheet.empty:
        return {"error": "Nemožno získať finančné výkazy pre tento ticker."}

    # 2. Získanie počtu akcií (Shares Outstanding)
    # yfinance neposkytuje historický počet akcií úplne spoľahlivo, použijeme aktuálny
    shares = stock.info.get('sharesOutstanding')

    # 3. Príprava výsledného DataFrame
    # Transponujeme, aby sme mali dátumy ako riadky
    df = pd.DataFrame(index=income_stmt.columns)

    # --- ZÁKLADNÉ ÚDAJE Z VÝKAZOV ---
    df['Revenue'] = income_stmt.loc['Total Revenue'] if 'Total Revenue' in income_stmt.index else None
    df['Net Income'] = income_stmt.loc['Net Income'] if 'Net Income' in income_stmt.index else None
    
    # Celkový dlh (Total Debt)
    if 'Total Debt' in balance_sheet.index:
        df['Debt'] = balance_sheet.loc['Total Debt']
    elif 'Long Term Debt' in balance_sheet.index:
        df['Debt'] = balance_sheet.loc['Long Term Debt'] + balance_sheet.get('Short Long Term Debt', 0)
    else:
        df['Debt'] = 0

    # Hotovosť
    cash = balance_sheet.loc['Cash And Cash Equivalents'] if 'Cash And Cash Equivalents' in balance_sheet.index else 0
    # Vlastné imanie (Book Value)
    book_value = balance_sheet.loc['Stockholders Equity'] if 'Stockholders Equity' in balance_sheet.index else None

    # --- VÝPOČTY ZÁVISLÉ NA CENE AKCIE ---
    market_caps = []
    pe_ratios = []
    ps_ratios = []
    pb_ratios = []
    ev_values = []

    for date in df.index:
        # Získame cenu akcie v daný deň (alebo najbližší pracovný deň)
        start_date = date.strftime('%Y-%m-%d')
        # Pridáme pár dní, aby sme mali istotu, že trafíme otvorený trh
        end_date = (date + pd.Timedelta(days=5)).strftime('%Y-%m-%d')
        hist = stock.history(start=start_date, end=end_date)
        
        if not hist.empty:
            price = hist['Close'].iloc[0]
            m_cap = price * shares
            
            market_caps.append(m_cap)
            ev_values.append(m_cap + df.loc[date, 'Debt'] - cash.get(date, 0))
            
            # Trailing P/E (zjednodušené na kvartálny zisk * 4)
            q_income = df.loc[date, 'Net Income']
            pe_ratios.append(m_cap / (q_income * 4) if q_income and q_income > 0 else None)
            
            # Price/Sales (Revenue * 4)
            rev = df.loc[date, 'Revenue']
            ps_ratios.append(m_cap / (rev * 4) if rev and rev > 0 else None)
            
            # Price/Book
            bv = book_value.get(date) if book_value is not None else None
            pb_ratios.append(m_cap / bv if bv and bv > 0 else None)
        else:
            market_caps.append(None)
            ev_values.append(None)
            pe_ratios.append(None)
            ps_ratios.append(None)
            pb_ratios.append(None)

    df['Market Cap'] = market_caps
    df['Enterprise Value'] = ev_values
    df['Trailing P/E'] = pe_ratios
    df['Price/Sales'] = ps_ratios
    df['Price/Book'] = pb_ratios
    
    # Forward P/E je odhad do budúcna, v historických dátach sa nachádza len ako aktuálny údaj
    df['Forward P/E (Current)'] = stock.info.get('forwardPE')

    # Vyčistíme formát (otočíme späť, aby boli dátumy v stĺpcoch ako na Yahoo)
    return df.sort_index(ascending=False).T.to_json()

# Test pre Apple
print(get_valuation_history("PLTR"))