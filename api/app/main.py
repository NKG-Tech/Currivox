# api/app/main.py
import os, base64
from io import BytesIO
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Request
from fastapi.responses import StreamingResponse, Response, JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from dotenv import load_dotenv

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from .security import make_middlewares
from .limits import limiter, MaxBodySizeMiddleware

# --- Optionnel: extraction avancée si dispo
try:
    from .extract import sniff_and_extract
except Exception:
    sniff_and_extract = None

# --- PDF simple (fallback)
try:
    from pypdf import PdfReader
except Exception:
    from PyPDF2 import PdfReader

load_dotenv()

# ---------- App + Middlewares ----------
app = FastAPI(title="CV Agent API", middleware=make_middlewares())
app.add_middleware(MaxBodySizeMiddleware)

# SlowAPI (rate-limit)
@app.middleware("http")
async def _rate_limit_mw(request: Request, call_next):
    route = request.url.path
    # limites un peu plus strictes sur endpoints chers
    special = {"/analyze-text": "20/minute", "/linkedin/optimize": "30/minute", "/ingest/pdf": "30/minute"}
    limit = special.get(route)
    if limit:
        with limiter.limit(limit)(lambda r: None)(request):
            return await call_next(request)
    else:
        return await call_next(request)

# ---------- Global error handlers ----------
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": exc.errors()}, status_code=422)

@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

# ---------- Prometheus ----------
REQUEST_COUNT = Counter("cvagent_requests_total", "Total API requests", ["route", "method", "status"])
REQUEST_LATENCY = Histogram("cvagent_request_latency_seconds", "Latency", ["route"])

@app.middleware("http")
async def metrics_mw(request: Request, call_next):
    route = request.url.path
    with REQUEST_LATENCY.labels(route=route).time():
        resp = await call_next(request)
    REQUEST_COUNT.labels(route=route, method=request.method, status=resp.status_code).inc()
    return resp

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ---------- Health ----------
@app.get("/")
def root():
    return {"ok": True, "service": "cv-agent-api"}

@app.get("/ping")
def ping():
    return {"pong": True}

# ---------- Upload / parsing (extract.py si dispo) ----------
@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    if sniff_and_extract is None:
        raise HTTPException(status_code=501, detail="Extraction non disponible (extract.py manquant).")
    data = await file.read()
    kind, text = sniff_and_extract(file.filename, data)
    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Texte non détecté (PDF scanné ?)")
    return {"kind": kind, "text": text[:50000]}

# ---------- Fallback PDF simple ----------
@app.post("/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="file required")
    # contrôle MIME & extension
    allowed = {"application/pdf", "application/octet-stream"}
    if file.content_type not in allowed or not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail=f"PDF only")
    raw = await file.read()
    reader = PdfReader(BytesIO(raw))
    texts = []
    for page in getattr(reader, "pages", []):
        texts.append(page.extract_text() or "")
    text = "\n".join(texts)
    return {"ok": True, "chars": len(text), "text": text[:200000]}

# ---------- Analyse LLM ----------
class AnalyzeTextIn(BaseModel):
    resume: str
    job: str
    language: str = "fr"
    gender: str = "auto"

@app.post("/analyze-text")
def analyze_text(payload: AnalyzeTextIn):
    try:
        from .llm import analyze_with_llm
    except Exception:
        raise HTTPException(status_code=501, detail="Analyse LLM indisponible (llm.py manquant/erreur).")
    return analyze_with_llm(payload.resume, payload.job, payload.language, payload.gender)

# ---------- Simulation entretien ----------
@app.post("/interview/generate")
def interview_generate(payload: Dict[str, Any] = Body(...)):
    try:
        from .interview import generate_questions
    except Exception:
        raise HTTPException(status_code=501, detail="Module interview indisponible.")
    return {
        "questions": generate_questions(
            payload.get("resume", "")[:20000],
            payload.get("job", "")[:8000],
            payload.get("language", "fr"),
        )
    }

@app.post("/interview/score")
def interview_score(payload: Dict[str, Any] = Body(...)):
    try:
        from .interview import score_answer
    except Exception:
        raise HTTPException(status_code=501, detail="Module interview indisponible.")
    return score_answer(payload.get("answer", "")[:4000], payload.get("job", "")[:4000])

# ---------- Réécriture CV ----------
@app.post("/cv/rewrite")
def cv_rewrite(payload: Dict[str, Any] = Body(...)):
    try:
        from .rewriter import rewrite_resume
    except Exception:
        raise HTTPException(status_code=501, detail="Module rewriter indisponible.")
    return rewrite_resume(
        payload.get("resume", "")[:20000],
        payload.get("job", "")[:8000],
        payload.get("language", "fr"),
    )

# ---------- LinkedIn ----------
class LinkedinPdfIn(BaseModel):
    headline: str
    about: str
    full_name: str = ""

@app.post("/linkedin/optimize")
def linkedin_optimize(payload: Dict[str, Any] = Body(...)):
    try:
        from .linkedin import optimize_linkedin
    except Exception:
        raise HTTPException(status_code=501, detail="Module linkedin indisponible.")
    return optimize_linkedin(
        payload.get("resume", "")[:20000],
        payload.get("job", "")[:8000],
        payload.get("language", "fr"),
        payload.get("gender", "auto"),
    )

@app.post("/linkedin/export/pdf")
def linkedin_export_pdf(payload: LinkedinPdfIn):
    try:
        from .exporter_linkedin import export_linkedin_pdf
    except Exception:
        raise HTTPException(status_code=501, detail="exporter_linkedin indisponible.")
    pdf = export_linkedin_pdf(payload.headline, payload.about, full_name=payload.full_name)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=linkedin.pdf"},
    )

@app.post("/linkedin/export/pdf-b64")
def linkedin_export_pdf_b64(payload: LinkedinPdfIn):
    try:
        from .exporter_linkedin import export_linkedin_pdf
    except Exception:
        raise HTTPException(status_code=501, detail="exporter_linkedin indisponible.")
    pdf = export_linkedin_pdf(payload.headline, payload.about, full_name=payload.full_name)
    b64 = base64.b64encode(pdf).decode("ascii")
    return {"filename": "linkedin.pdf", "mime": "application/pdf", "data": b64}

# ---------- Exports génériques ----------
@app.post("/export/docx")
def export_as_docx(payload: Dict[str, Any] = Body(...)):
    try:
        from .exporter import export_docx
    except Exception:
        raise HTTPException(status_code=501, detail="exporter.export_docx indisponible.")
    data = {
        "title": payload.get("title", "CV optimisé"),
        "headline": payload.get("headline"),
        "bullets": payload.get("bullets", []),
        "skills": payload.get("skills", []),
        "about": payload.get("about", ""),
    }
    content = export_docx(data)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=cv_optimise.docx"},
    )

@app.post("/export/pdf")
def export_as_pdf(payload: Dict[str, Any] = Body(...)):
    try:
        from .exporter import export_pdf
    except Exception:
        raise HTTPException(status_code=501, detail="exporter.export_pdf indisponible.")
    title = payload.get("title", "Lettre")
    text = payload.get("text", "")
    pdf_bytes = export_pdf(text[:20000], title[:200])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=lettre.pdf"},
    )
