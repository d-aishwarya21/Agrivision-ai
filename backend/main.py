from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app import models
from app.routers import auth, diagnose, history

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CausalAg-Net API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(diagnose.router)
app.include_router(history.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}