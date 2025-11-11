from fastapi import FastAPI
from .config import settings
from .db import init_db
from .routers import auth, travel, ai, map as map_router, speech

app = FastAPI(title=settings.APP_NAME)


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
