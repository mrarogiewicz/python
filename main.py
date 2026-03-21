import random
import string
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def get_random_string():
    # Vygeneruje náhodný reťazec o dĺžke 10 znakov
    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for i in range(10))
    
    return {
        "status": "success",
        "random_string": result_str
    }
