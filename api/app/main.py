
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="CV Agent API - Minimal")

# CORS: autorise ton front local
origins = (os.getenv("CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "service": "cv-agent-api-minimal"}

# exemple d’endpoint pour tester rapidement
@app.get("/ping")
def ping():
    return {"pong": True}
import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

load_dotenv()

app = FastAPI(title="CV Agent API")

origins = (os.getenv("CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Prometheus metrics ---
REQUEST_COUNT = Counter("cvagent_requests_total", "Total API requests", ["route", "method", "status"])
REQUEST_LATENCY = Histogram("cvagent_request_latency_seconds", "Latency", ["route"])

@app.middleware("http")
async def prometheus_middleware(request, call_next):
    route = request.url.path
    with REQUEST_LATENCY.labels(route=route).time():
        response = await call_next(request)
    REQUEST_COUNT.labels(route=route, method=request.method, status=response.status_code).inc()
    return response

@app.get("/")
def root():
    return {"ok": True, "service": "cv-agent-api"}

@app.get("/ping")
def ping():
    return {"pong": True}

# --- New endpoints (stubs) ---

@app.post("/analyze")
async def analyze(payload: Dict[str, Any] = Body(...)):
    """
    payload = { "resume": "...", "job": "...", "options": {...} }
    TODO: appeler GROQ / ton moteur d'analyse et renvoyer scoring + recommandations.
    """
    resume = payload.get("resume", "")
    job = payload.get("job", "")
    if not resume or not job:
        raise HTTPException(status_code=400, detail="resume and job are required")
    # TODO: implement real analysis
    return {"ok": True, "analysis": {"match_score": 0.82, "highlights": [], "next_steps": []}}

@app.post("/linkedin")
async def linkedin(payload: Dict[str, Any] = Body(...)):
    """
    TODO: générer résumé de profil, mots-clés, bullet points, etc.
    """
    profile_url = payload.get("profile_url")
    if not profile_url:
        raise HTTPException(status_code=400, detail="profile_url is required")
    return {"ok": True, "profile_url": profile_url, "summary": "TODO"}

@app.post("/export/pdf")
async def export_pdf(payload: Dict[str, Any] = Body(...)):
    """
    TODO: Générer un PDF à partir des données analysées.
    Pour l’instant, stub qui confirme la requête.
    """
    data = payload.get("data")
    if not data:
        raise HTTPException(status_code=400, detail="data is required")
    return {"ok": True, "status": "queued", "note": "PDF export stub"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
