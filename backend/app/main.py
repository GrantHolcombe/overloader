import hmac

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import auth, exercises

settings = get_settings()
if settings.env != "dev" and settings.jwt_secret == "dev-only-change-me":
    raise RuntimeError("Set JWT_SECRET outside dev")

app = FastAPI(title="Overloader API", version="0.1.0")


@app.middleware("http")
async def require_origin_secret(request: Request, call_next):
    """With ORIGIN_SECRET set, only requests that came through Cloudflare (which adds the
    X-Origin-Verify header) get in. /api/health stays open for the Lambda Web Adapter's
    readiness check, which comes from inside the container."""
    secret = get_settings().origin_secret
    if secret and request.url.path != "/api/health":
        given = request.headers.get("x-origin-verify", "")
        if not hmac.compare_digest(given.encode(), secret.encode()):
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return await call_next(request)


if settings.cors_origin_list:
    # Added after the origin check, so it wraps it: browsers still see CORS headers on a 403.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(auth.router)
app.include_router(exercises.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
