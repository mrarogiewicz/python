import random
import string
import os
import asyncio
import base64
import re
from pathlib import Path
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException, Query
from playwright.async_api import async_playwright


app = FastAPI()

# Načítanie kľúča z prostredia Renderu
# Ak kľúč v Renderi neexistuje, použije sa "default_tajny_kluc" (len pre testovanie)
VALID_API_KEY = os.environ.get("API_KEY")




# --- Kompatibilita s Jupyter / IPython (už bežiaci event loop) ---
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # V bežnom Pythone nie je potrebný


URL = "https://finance.yahoo.com/quote/PLTR/key-statistics/"
OUTPUT_FILE = "PLTR_financials.html"  # napríklad Downloads
EXTRA_WAIT_MS = 3000


async def embed_resources(page, html: str, base_url: str) -> str:

    # Inline CSS
    css_links = re.findall(
        r'<link[^>]+rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    for href in css_links:
        full_url = urljoin(base_url, href)
        try:
            response = await page.request.get(full_url)
            if response.ok:
                css_text = await response.text()
                tag_pattern = re.compile(
                    r'<link[^>]+href=["\']' + re.escape(href) + r'["\'][^>]*/?>',
                    re.IGNORECASE,
                )
                html = tag_pattern.sub(f"<style>{css_text}</style>", html, count=1)
        except Exception as e:
            print(f"  [WARN] CSS skip: {href} → {e}")

    # Inline obrázky ako base64
    img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for src in set(img_srcs):
        if src.startswith("data:"):
            continue
        full_url = urljoin(base_url, src)
        try:
            response = await page.request.get(full_url)
            if response.ok:
                content_type = response.headers.get("content-type", "image/png").split(";")[0]
                body = await response.body()
                b64 = base64.b64encode(body).decode()
                data_uri = f"data:{content_type};base64,{b64}"
                html = html.replace(f'src="{src}"', f'src="{data_uri}"')
                html = html.replace(f"src='{src}'", f"src='{data_uri}'")
        except Exception as e:
            print(f"  [WARN] IMG skip: {src} → {e}")

    return html


async def main():
    output_path = Path(OUTPUT_FILE)
    print(f"▶  Spúšťam Chromium a načítavam: {URL}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        page = await context.new_page()

        print("⏳  Čakám na dokončenie renderovania (networkidle)…")
        await page.goto(URL, wait_until="networkidle", timeout=60_000)

        # Pokus o zatvorenie cookie/consent dialógu
        for selector in ["button[name='agree']", "#consent-dialog button", ".accept-all"]:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

        print(f"⏳  Extra čakanie {EXTRA_WAIT_MS} ms na async dáta…")
        await page.wait_for_timeout(EXTRA_WAIT_MS)

        html = await page.content()
        base_url = page.url

        print("📦  Vkladám CSS a obrázky inline (base64)…")
        html = await embed_resources(page, html, base_url)

        await browser.close()

    output_path.write_text(html, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"\n✅  Hotovo! Súbor uložený: {output_path.resolve()}")
    print(f"   Veľkosť: {size_kb:,.0f} KB")
    print(f"   Otvor v prehliadači: file://{output_path.resolve()}")





@app.get("/")
def get_random_string(key: str = Query(None)):
    # 1. Kontrola, či používateľ vôbec poslal kľúč
    if not key:
        raise HTTPException(status_code=401, detail="Chyba: Chýba API kľúč.")

    # 2. Porovnanie zaslaného kľúča s tým v Renderi
    if key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Chyba: Nesprávny API kľúč.")

    # 3. Ak je kľúč správny, vygeneruje sa string
    letters = string.ascii_letters
    result_str = 'AAAAA'.join(random.choice(letters) for i in range(10))
    
# --- Spustenie kompatibilné s Jupyter aj bežným Pythonom ---
    try:
        loop = asyncio.get_running_loop()
        # Sme v Jupyter / IPython — loop už beží, použijeme nest_asyncio
        loop.run_until_complete(main())
    except RuntimeError:
        # Bežný Python — žiadny loop, spustíme štandardne
        asyncio.run(main())
        
    return {
        "status": "success",
        "random_string": result_str
    }
