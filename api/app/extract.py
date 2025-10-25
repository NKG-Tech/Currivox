# api/app/extract.py
from __future__ import annotations

def sniff_and_extract(filename: str, data: bytes) -> tuple[str, str]:
    """
    Extracteur minimal :
    - Essaie de décoder comme texte brut (utf-8).
    - Si échec -> renvoie ('bin', '') proprement, sans casser l'API.
    Remplace-le plus tard par ton vrai extracteur PDF/DOCX si besoin.
    """
    name = (filename or "").lower()
    # Heuristique basique
    for enc in ("utf-8", "latin-1"):
        try:
            text = data.decode(enc)
            kind = "txt"
            return (kind, text)
        except Exception:
            pass
    # Rien de lisible
    return ("bin", "")
