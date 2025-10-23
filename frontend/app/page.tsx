'use client';

import { useState } from 'react';

// URL API (avec fallback)
const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000';

type AnalyzeResult = {
  match_score: number;
  missing_keywords: string[];
  suggestions: string[];
  profile_summary: string;
  cover_letter: string;
};

export default function Home() {
  const [resumeText, setResumeText] = useState('');
  const [jobText, setJobText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function uploadFile(file: File) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API}/resume/upload`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error('Upload résumé failed');
    const data = await res.json();
    setResumeText(data.text || '');
  }

  async function analyze() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/analyze-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume: resumeText, job: jobText, language: 'fr' })
      });
      if (!res.ok) throw new Error(await res.text());
      const data: AnalyzeResult = await res.json();
      setResult((r: any) => ({ ...(r || {}), analyze: data }));
    } catch (e: any) {
      setToast(e.message || 'Erreur analyse');
    } finally {
      setLoading(false);
    }
  }

  async function rewriteCV() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/cv/rewrite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume: resumeText, job: jobText, language: 'fr' })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult((r: any) => ({ ...(r || {}), rewrite: data }));
    } catch (e: any) {
      setToast(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function generateInterview() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/interview/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume: resumeText, job: jobText, language: 'fr' })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult((r: any) => ({
        ...(r || {}),
        questions: data.questions,
        currentQ: 0,
        answers: [],
        tmpAns: ''
      }));
    } catch (e: any) {
      setToast(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function scoreAnswer() {
    const q = result?.questions?.[result?.currentQ || 0];
    const a = result?.tmpAns || '';
    if (!q || !a) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/interview/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: a, job: jobText })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const next = Math.min((result.currentQ || 0) + 1, 4);
      setResult((r: any) => ({
        ...r,
        tmpAns: '',
        answers: [...(r?.answers || []), { q, a, ...data }],
        currentQ: next
      }));
    } catch (e: any) {
      setToast(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function linkedin() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/linkedin/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume: resumeText, job: jobText, language: 'fr' })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult((r: any) => ({ ...(r || {}), linkedin: data }));
    } catch (e: any) {
      setToast(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function exportDocx() {
    if (!result?.rewrite) return;
    const payload = {
      headline: result.rewrite.headline,
      bullets: result.rewrite.bullets,
      skills: result.rewrite.skills
    };
    const res = await fetch(`${API}/export/docx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      setToast(await res.text());
      return;
    }
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'cv_optimise.docx';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function exportAboutPdf() {
    const headline: string = result?.linkedin?.headline || '';
    const about: string = result?.linkedin?.about || '';
    const fullName: string = result?.fullName || '';

    if (!about) {
      alert('Pas de texte About.');
      return;
    }
    try {
      const res = await fetch(`${API}/linkedin/export/pdf-b64`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headline, about, full_name: fullName })
      });

      if (!res.ok) {
        let msg = '';
        try { msg = await res.text(); } catch {}
        throw new Error(`HTTP ${res.status}: ${msg || 'échec export PDF'}`);
      }

      const { filename, data, mime } = await res.json();
      const bytes = Uint8Array.from(atob(data), c => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], { type: mime || 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'linkedin.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`Export PDF: ${e?.message || e}`);
    }
  }

  return (
    <main className="mx-auto max-w-6xl p-6 space-y-8">
      <h1 className="text-3xl font-semibold">CV Agent</h1>
      {toast && (
        <div className="bg-red-100 text-red-700 p-3 rounded" onClick={() => setToast(null)}>
          {toast}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-4 shadow">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Ton CV (texte)</h3>
            <label className="px-3 py-2 bg-black text-white rounded cursor-pointer">
              Importer CV (PDF/DOCX)
              <input
                type="file"
                className="hidden"
                onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) uploadFile(f).catch(err => setToast(String(err)));
                }}
              />
            </label>
          </div>
          <textarea
            className="mt-3 w-full border rounded p-2 min-h-[220px]"
            value={resumeText}
            onChange={e => setResumeText(e.target.value)}
          />
        </div>

        <div className="bg-white rounded-2xl p-4 shadow">
          <h3 className="font-medium">Offre d’emploi</h3>
          <textarea
            className="mt-3 w-full border rounded p-2 min-h-[220px]"
            value={jobText}
            onChange={e => setJobText(e.target.value)}
          />
        </div>
      </div>

      <button
        className="px-5 py-2 rounded bg-black text-white disabled:opacity-60"
        disabled={loading}
        onClick={analyze}
      >
        {loading ? 'Analyse en cours…' : 'Analyser'}
      </button>

      {result?.analyze && (
        <section className="space-y-6">
          <div className="flex items-center gap-4 mt-6">
            <div className="w-16 h-16 rounded-full bg-black text-white flex items-center justify-center text-2xl">
              {result.analyze.match_score}
            </div>
            <div className="text-gray-700">Score d’adéquation (0–100)</div>
          </div>

          <div>
            <h3 className="font-medium mb-2">Mots-clés manquants</h3>
            <div className="flex flex-wrap gap-2">
              {result.analyze.missing_keywords?.map((k: string, i: number) => (
                <span key={i} className="px-2 py-1 rounded bg-gray-100 text-sm">
                  {k}
                </span>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-medium mb-2">Suggestions</h3>
            <ul className="list-disc pl-6 space-y-1">
              {result.analyze.suggestions?.map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-medium mb-2">Résumé de profil</h3>
            <div className="bg-white rounded-2xl p-4 shadow">{result.analyze.profile_summary}</div>
          </div>

          <div>
            <h3 className="font-medium mb-2">Lettre de motivation</h3>
            <div className="bg-white rounded-2xl p-4 shadow whitespace-pre-wrap">
              {result.analyze.cover_letter}
            </div>
          </div>
        </section>
      )}

      <section className="bg-white rounded-2xl p-4 shadow space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Réécriture ciblée (headline, bullets, skills)</h3>
          <button
            className="px-3 py-2 bg-black text-white rounded disabled:opacity-60"
            disabled={loading}
            onClick={rewriteCV}
          >
            Réécrire
          </button>
        </div>
        {result?.rewrite && (
          <div className="space-y-3">
            <div><b>Headline :</b> {result.rewrite.headline}</div>
            <div>
              <b>Bullets :</b>
              <ul className="list-disc pl-6">
                {result.rewrite.bullets?.map((b: string, i: number) => <li key={i}>{b}</li>)}
              </ul>
            </div>
            <div><b>Skills :</b> {result.rewrite.skills?.join(', ')}</div>
            <div>
              <button className="px-3 py-2 bg-gray-900 text-white rounded" onClick={exportDocx}>
                Exporter DOCX
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="bg-white rounded-2xl p-4 shadow space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Simulation d’entretien</h3>
          <button
            className="px-3 py-2 bg-black text-white rounded disabled:opacity-60"
            disabled={loading}
            onClick={generateInterview}
          >
            Générer 5 questions
          </button>
        </div>

        {Array.isArray(result?.questions) && result.questions.length > 0 && (
          <div className="space-y-3">
            <div>
              <b>Question {(result.currentQ ?? 0) + 1}/5 :</b> {result.questions[result.currentQ]}
            </div>
            <textarea
              className="w-full border rounded p-2"
              rows={4}
              value={result.tmpAns || ''}
              onChange={e => setResult((r: any) => ({ ...r, tmpAns: e.target.value }))}
            />
            <button
              className="px-3 py-2 bg-gray-900 text-white rounded disabled:opacity-60"
              disabled={loading}
              onClick={scoreAnswer}
            >
              Soumettre
            </button>

            {Array.isArray(result?.answers) && result.answers.length > 0 && (
              <div className="space-y-2">
                {result.answers.map((x: any, i: number) => (
                  <div key={i} className="border rounded p-2">
                    <div className="text-sm text-gray-600">Q{i + 1}. {x.q}</div>
                    <div className="text-sm">Score: <b>{x.score}</b> — Tips: {x.tips.join(' • ')}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      <section className="bg-white rounded-2xl p-4 shadow space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">LinkedIn (About + Headline)</h3>
          <button
            className="px-3 py-2 bg-black text-white rounded disabled:opacity-60"
            disabled={loading}
            onClick={linkedin}
          >
            Générer
          </button>
        </div>
        {result?.linkedin && (
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-500 mb-1">Headline</div>
              <div className="border rounded p-2">{result.linkedin.headline}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-1">About</div>
              <div className="border rounded p-2 whitespace-pre-wrap">{result.linkedin.about}</div>
            </div>
            <div className="md:col-span-2">
              <button className="px-3 py-2 bg-gray-900 text-white rounded" onClick={exportAboutPdf}>
                Exporter About en PDF
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
