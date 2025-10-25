# api/app/llm.py
import os, time, json
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

API_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT = (5, 30)  # (connect, read) secondes
RETRIES = 2

def _post_with_retry(payload: dict):
    last_err = None
    for i in range(RETRIES + 1):
        try:
            r = requests.post(API_URL, headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }, json=payload, timeout=TIMEOUT)
            if r.status_code >= 500:
                last_err = RuntimeError(f"upstream {r.status_code}")
                time.sleep(0.7 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(0.5 * (i + 1))
    raise last_err

def analyze_with_llm(resume: str, job: str, language="fr", gender="auto"):
    if not GROQ_API_KEY:
        return {"ok": False, "error": "GROQ_API_KEY missing"}

    # Coupe les inputs (défense contre payloads énormes)
    resume = (resume or "")[:20000]
    job    = (job or "")[:8000]

    prompt = f"""
Tu es un expert RH. Analyse le CV vs l'offre ci-dessous.
Réponds en JSON *valide* avec clés: "score", "forces", "manques", "reco", "mots_cles".
Langue: {language}, Genre: {gender}

[CV]
{resume}

[OFFRE]
{job}
    """.strip()

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }

    data = _post_with_retry(payload)
    content = data["choices"][0]["message"]["content"]

    # Essaye de parser en JSON. Si c’est du texte, encapsule proprement.
    try:
        parsed = json.loads(content)
        return {"ok": True, "model": GROQ_MODEL, **parsed}
    except Exception:
        return {"ok": True, "model": GROQ_MODEL, "result_raw": content}
