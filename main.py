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

VALID_API_KEY = os.environ.get("API_KEY")

URL = "https://finance.yahoo.com/quote/PLTR/key-statistics/"
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


async def scrape() -> str:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",               # nutné pre Render / Docker prostredie
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",    # obmedzená /dev/shm na Renderi
                "--disable-gpu",
            ],
        )
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

        print(f"⏳ Načítavam: {URL}")
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

        print(f"⏳ Extra čakanie {EXTRA_WAIT_MS} ms…")
        await page.wait_for_timeout(EXTRA_WAIT_MS)

        html = await page.content()
        base_url = page.url

        print("📦 Vkladám resources inline…")
        html = await embed_resources(page, html, base_url)

        await browser.close()  # ← len raz!

    return html


@app.get("/")
async def get_page(key: str = Query(None)):  # ← async! FastAPI beží na asyncio
    if not key:
        raise HTTPException(status_code=401, detail="Chyba: Chýba API kľúč.")
    if key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Chyba: Nesprávny API kľúč.")

    html = await scrape()  # priamo await, bez loop.run_until_complete
    return html