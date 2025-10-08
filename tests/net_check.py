from dotenv import load_dotenv; load_dotenv(override=True)
import os, httpx, certifi

api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
print("API prefix:", api_key[:12])

headers = {"Authorization": f"Bearer {api_key}"}
url = "https://api.openai.com/v1/models"

# fuerza bundle de certificados conocido
with httpx.Client(timeout=20.0, verify=certifi.where()) as c:
    r = c.get(url, headers=headers)
    print("Status:", r.status_code)
    print("OK?", r.status_code == 200)
    print("Body head:", r.text[:120])
