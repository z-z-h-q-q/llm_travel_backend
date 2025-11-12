from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import init_db
from .routers import auth, travel, ai, map as map_router, speech

app = FastAPI(title=settings.APP_NAME)

# CORS: allow frontend to make requests (including preflight OPTIONS)
# In development it's convenient to allow all origins; in production restrict this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth.router)
app.include_router(travel.router)
app.include_router(ai.router)
app.include_router(map_router.router)
app.include_router(speech.router)


@app.get("/")
def root():
    return {"ok": True, "app": settings.APP_NAME}
