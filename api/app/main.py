# api/app/main.py
import os
import base64
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv

# --- extract: obligatoire seulement pour /resume/upload
try:
    from .extract import sniff_and_extract
except Exception:
    sniff_and_extract = None  # on gère proprement plus bas

load_dotenv()

app = FastAPI(title="CV Agent API - Minimal")

# CORS (front local par défaut)
origins = (os.getenv("CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------- Health ----------------------
@app.get("/")
def root():
    return {"ok": True, "service": "cv-agent-api-minimal"}

@app.get("/ping")
def ping():
    return {"pong": True}

# ---------------------- Upload / parsing CV ----------------------
@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    if sniff_and_extract is None:
        raise HTTPException(status_code=501, detail="Extraction non disponible (extract.py manquant).")
    data = await file.read()
    kind, text = sniff_and_extract(file.filename, data)
    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Texte non détecté (PDF scanné ?)")
    return {"kind": kind, "text": text[:50000]}

# ---------------------- Analyse LLM ----------------------
class AnalyzeTextIn(BaseModel := __import__("pydantic").__dict__["BaseModel"]):
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

# ---------------------- Simulation entretien ----------------------
@app.post("/interview/generate")
def interview_generate(payload: Dict[str, Any] = Body(...)):
    try:
        from .interview import generate_questions
    except Exception:
        raise HTTPException(status_code=501, detail="Module interview indisponible.")
    return {
        "questions": generate_questions(
            payload.get("resume", ""),
            payload.get("job", ""),
            payload.get("language", "fr"),
        )
    }

@app.post("/interview/score")
def interview_score(payload: Dict[str, Any] = Body(...)):
    try:
        from .interview import score_answer
    except Exception:
        raise HTTPException(status_code=501, detail="Module interview indisponible.")
    return score_answer(payload.get("answer", ""), payload.get("job", ""))

# ---------------------- Réécriture CV ----------------------
@app.post("/cv/rewrite")
def cv_rewrite(payload: Dict[str, Any] = Body(...)):
    try:
        from .rewriter import rewrite_resume
    except Exception:
        raise HTTPException(status_code=501, detail="Module rewriter indisponible.")
    return rewrite_resume(
        payload.get("resume", ""),
        payload.get("job", ""),
        payload.get("language", "fr"),
    )

# ---------------------- LinkedIn (About + Headline) ----------------------
@app.post("/linkedin/optimize")
def linkedin_optimize(payload: Dict[str, Any] = Body(...)):
    try:
        from .linkedin import optimize_linkedin
    except Exception:
        raise HTTPException(status_code=501, detail="Module linkedin indisponible.")
    return optimize_linkedin(
        payload.get("resume", ""),
        payload.get("job", ""),
        payload.get("language", "fr"),
        payload.get("gender", "auto"),
    )

# ---------------------- Export LinkedIn PDF ----------------------
class LinkedinPdfIn(BaseModel):  # réutilise pydantic importé plus haut
    headline: str
    about: str
    full_name: str = ""

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

# ---------------------- Exports génériques (DOCX/PDF) ----------------------
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
    pdf_bytes = export_pdf(text, title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=lettre.pdf"},
    )

# ---------------------- Lettre “administration publique” ----------------------
class LetterIn(BaseModel):
    full_name: str = ""
    body: str

@app.post("/letter/admin/pdf")
def letter_admin_pdf(payload: LetterIn):
    try:
        from .exporter_letter import export_letter_pdf
    except Exception:
        raise HTTPException(status_code=501, detail="exporter_letter indisponible.")
    pdf_bytes = export_letter_pdf(payload.body, full_name=payload.full_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=lettre_admin.pdf"},
    )
