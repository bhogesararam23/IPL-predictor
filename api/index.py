import sys
import os
from pathlib import Path

# Add ipl-engine to sys.path so we can import backend
sys.path.append(str(Path(__file__).resolve().parent.parent / "ipl-engine"))

from fastapi import Request
from backend.main import app
from mangum import Mangum

# Mount a /api/test route for debugging
@app.get("/api/test")
async def api_test():
    return {"status": "ok", "message": "Backend is running correctly"}

# Vercel passes requests with /api/simulate. We want to route them correctly.
# We'll rely on the frontend explicitly calling /api/simulate, but backend routes are /simulate.
# A middleware to strip /api prefix from path for FastAPI internal routing
@app.middleware("http")
async def rewrite_api_requests(request: Request, call_next):
    if request.scope["path"].startswith("/api"):
        request.scope["path"] = request.scope["path"][4:] or "/"
    response = await call_next(request)
    return response

# Mangum adapter for Vercel/AWS Serverless integration
handler = Mangum(app)
