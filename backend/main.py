from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Fantasy Matchup Engine",
    version="0.1.0",
    description="Fantasy football matchup, projection, and lineup optimization API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/status")
def status():
    return {
        "app": "fantasy-matchup-engine",
        "version": "0.1.0",
        "projection_models": [
            "original",
            "cb_challenger",
            "full_cb_challenger",
        ],
        "status": "foundation_ready",
    }
