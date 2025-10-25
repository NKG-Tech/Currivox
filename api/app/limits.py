# api/app/limits.py
import os
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiteur en mémoire (simple). Pour de la prod à gros trafic, plug Redis Storage.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Limite de taille upload (fail fast)
class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.max_mb = int(os.getenv("MAX_UPLOAD_MB", "8"))
        self.max_bytes = self.max_mb * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        # Content-Length connu → vérification immédiate
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > self.max_bytes:
            return JSONResponse({"detail": f"Payload too large (> {self.max_mb} MB)"}, status_code=413)
        return await call_next(request)
