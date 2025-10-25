"use client";

import { useState } from "react";

const API_PUBLIC = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export default function Home() {
  const [resume, setResume] = useState("");
  const [job, setJob] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [ping, setPing] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [liHeadline, setLiHeadline] = useState("");
  const [liAbout, setLiAbout] = useState("");

  const notifyError = (e) => setErrorMsg(typeof e === "string" ? e : String(e));

  async function doPing() {
    setErrorMsg("");
    try {
      const res = await fetch("/api/ping", { cache: "no-store" });
      if (!res.ok) throw new Error(`/api/ping ${res.status}`);
      setPing(await res.json());
    } catch (e) { notifyError(e); }
  }

  async function handleImport(file) {
    setErrorMsg("");
    try {
      const form = new FormData();
      form.append("file", file);

      let res = await fetch("/api/resume/upload", { method: "POST", body: form });
      if (!res.ok && (res.status === 404 || res.status === 501)) {
        res = await fetch("/api/ingest/pdf", { method: "POST", body: form });
      }
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`upload failed: ${res.status} ${t}`);
      }
      const data = await res.json();
      setResume((data.text || "").trim());
    } catch (e) { notifyError(e); }
  }

  async function doAnalyze() {
    setErrorMsg("");
    setAnalysis(null);
    try {
      const res = await fetch("/api/analyze-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume, job, language: "fr", gender: "auto" }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`/api/analyze-text ${res.status} ${t}`);
      }
      setAnalysis(await res.json());
    } catch (e) { notifyError(e); }
  }

  async function optimizeLinkedIn() {
    setErrorMsg("");
    try {
      const res = await fetch("/api/linkedin/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume, job, language: "fr", gender: "auto" }),
      });
      if (!res.ok) throw new Error(`/api/linkedin/optimize ${res.status}`);
      const data = await res.json();
      setLiHeadline(data?.headline || "");
      setLiAbout(data?.about || data?.summary || "");
    } catch (e) { notifyError(e); }
  }

  async function exportPdf() {
    setErrorMsg("");
    try {
      const res = await fetch("/api/export/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Lettre",
          text: liHeadline || liAbout ? `${liHeadline}\n\n${liAbout}` : resume.slice(0, 2000),
        }),
      });
      if (!res.ok) throw new Error(`/api/export/pdf ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "lettre.pdf"; document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) { notifyError(e); }
  }

  return (
    <main style={{ maxWidth: 1100, margin: "32px auto", padding: 16 }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>CV Agent</h1>

      {errorMsg && (
        <div style={{ background:"#fde2e1", border:"1px solid #f6b1ad", padding:12, borderRadius:10, color:"#7a1d1a", marginBottom:16 }}>
          {errorMsg}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={doPing} style={btn}>Tester /ping</button>
        <a href={`${API_PUBLIC}/metrics`} target="_blank" rel="noreferrer" style={{ ...btn, textDecoration: "none" }}>
          Ouvrir /metrics
        </a>
      </div>

      {ping && <pre style={pre}>{JSON.stringify(ping, null, 2)}</pre>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginTop: 16 }}>
        <section style={card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={h2}>Ton CV (texte)</h2>
            <label style={{ ...btn, cursor: "pointer" }}>
              Importer CV (PDF/DOCX)
              <input
                type="file"
                accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                style={{ display: "none" }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImport(f); }}
              />
            </label>
          </div>
          <textarea value={resume} onChange={(e) => setResume(e.target.value)} rows={12} style={ta} />
        </section>

        <section style={card}>
          <h2 style={h2}>Offre d’emploi</h2>
          <textarea value={job} onChange={(e) => setJob(e.target.value)} rows={12} style={ta} />
        </section>
      </div>

      <div style={{ marginTop: 14 }}>
        <button onClick={doAnalyze} style={btn}>Analyser</button>
      </div>

      {analysis && (
        <section style={{ ...card, marginTop: 16 }}>
          <h2 style={h2}>Résultat analyse</h2>
          <pre style={pre}>{JSON.stringify(analysis, null, 2)}</pre>
        </section>
      )}

      <section style={{ ...card, marginTop: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <h2 style={h2}>LinkedIn (About + Headline)</h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={optimizeLinkedIn} style={btn}>Générer</button>
            <button onClick={exportPdf} style={btn}>Exporter PDF</button>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <div style={label}>Headline</div>
            <textarea rows={4} style={ta} value={liHeadline} onChange={(e) => setLiHeadline(e.target.value)} />
          </div>
          <div>
            <div style={label}>About</div>
            <textarea rows={6} style={ta} value={liAbout} onChange={(e) => setLiAbout(e.target.value)} />
          </div>
        </div>
      </section>
    </main>
  );
}

const card = { border: "1px solid #eee", borderRadius: 14, padding: 14, background: "#fff" };
const h2 = { fontSize: 18, fontWeight: 700, marginBottom: 8 };
const label = { fontWeight: 600, marginBottom: 6 };
const ta = { width: "100%", borderRadius: 10, border: "1px solid #ddd", padding: 10, fontFamily: "inherit" };
const btn = { padding: "10px 14px", borderRadius: 10, border: "1px solid #ddd", background: "#111", color: "#fff", cursor: "pointer" };
const pre = { background: "#0b1020", color: "#e7ecff", padding: 12, borderRadius: 10, overflowX: "auto", marginTop: 12 };
