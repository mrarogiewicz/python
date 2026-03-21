import random
import string
import os
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

# Načítanie kľúča z prostredia Renderu
# Ak kľúč v Renderi neexistuje, použije sa "default_tajny_kluc" (len pre testovanie)
VALID_API_KEY = os.environ.get("API_KEY")

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
    
    return {
        "status": "success",
        "random_string": result_str
    }
