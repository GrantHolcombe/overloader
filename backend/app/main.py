from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, exercises

settings = get_settings()
if settings.env != "dev" and settings.jwt_secret == "dev-only-change-me":
    raise RuntimeError("Set JWT_SECRET outside dev")

app = FastAPI(title="Overloader API", version="0.1.0")

if settings.cors_origin_list:
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
