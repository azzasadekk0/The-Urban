from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes.chat import router as chat_router
from backend.api.routes.health import router as health_router
from backend.config import settings

app = FastAPI(
    title="The Urban — Egyptian Building Code AI",
    description="Agentic RAG system for Egyptian Building Codes and Urban Regulations.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(health_router)


@app.on_event("startup")
async def startup_event():
    """Ensure data directories exist on startup."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    print("[OK] The Urban backend started.")
    print(f"   PDFs expected in: {settings.DATA_DIR}")
    print(f"   Vector DB at:     {settings.VECTOR_DB_DIR}")
    print(f"   API docs:         http://localhost:{settings.BACKEND_PORT}/docs")
