# api/app/security.py
import os, re
from typing import Iterable, Optional
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# --- En-têtes de sécurité simples (sans CSP avancée pour l’instant)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp: Response = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Permissions-Policy",
            "accelerometer=(), autoplay=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
        )
        resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        resp.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        return resp

def make_middlewares() -> list[Middleware]:
    # Trusted hosts
    raw_hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1").split(",")
    hosts = [h.strip() for h in raw_hosts if h.strip()]
    if "*" in hosts:  # sécurité : évite wildcard involontaire
        hosts = ["*"]

    # CORS
    origins = (os.getenv("CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000").split(",")
    origins = [o.strip() for o in origins if o.strip()]
    allow_regex = os.getenv("ALLOW_ORIGIN_REGEX")  # ex: ^https://.*\.vercel\.app$

    cors_kwargs = dict(
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    if allow_regex:
        cors_kwargs["allow_origin_regex"] = allow_regex
    else:
        cors_kwargs["allow_origins"] = origins

    return [
        Middleware(HTTPSRedirectMiddleware),            # force HTTPS (Render effectue TLS termin., garde tout de même)
        Middleware(TrustedHostMiddleware, allowed_hosts=hosts),
        Middleware(CORSMiddleware, **cors_kwargs),
        Middleware(SecurityHeadersMiddleware),
        # Optionnel si un jour tu poses des cookies (CSRF, etc.)
        Middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-not-secret")),
    ]
