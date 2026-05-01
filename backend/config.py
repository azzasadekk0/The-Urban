import os
import sys

# ── CRITICAL: Disable LangSmith/LangChain tracing BEFORE any langchain import ──
# Without this, LangGraph makes a blocking HTTPS call on import that hangs
# indefinitely when there is no network access or a corporate proxy blocks it.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_TRACING", "false")
os.environ.setdefault("LANGSMITH_API_KEY", "")
os.environ.setdefault("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_TRACING"] = "false"

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_LLM_MODEL: str = "gpt-4o"

    # Paths
    DATA_DIR: Path = BASE_DIR / "data" / "pdfs"
    VECTOR_DB_DIR: Path = BASE_DIR / "vector_db"
    SQLITE_DB_PATH: Path = BASE_DIR / "sessions.db"

    # RAG Settings
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_PER_TIER: int = 3

    # Backend
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8001")
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8001

    # Document Priority Registry
    # Priority 1 = highest authority. Priority 6 = lowest (suppressible).
    DOCUMENT_REGISTRY: list = [
        {
            "filename": "decree_943_2024.pdf",
            "collection": "decree_943_2024",
            "law_name": "مرسوم 943 لسنة 2024",
            "law_name_en": "Decree 943/2024",
            "priority": 1,
            "can_be_suppressed": False,
        },
        {
            "filename": "law_119_2008.pdf",
            "collection": "law_119_2008",
            "law_name": "قانون البناء الموحد 119 لسنة 2008",
            "law_name_en": "Unified Building Law 119/2008",
            "priority": 2,
            "can_be_suppressed": False,
        },
        {
            "filename": "executive_regulations_119.pdf",
            "collection": "executive_regulations_119",
            "law_name": "اللائحة التنفيذية للقانون 119",
            "law_name_en": "Executive Regulations of Law 119",
            "priority": 3,
            "can_be_suppressed": False,
        },
        {
            "filename": "law_187_2023.pdf",
            "collection": "law_187_2023",
            "law_name": "قانون 187 لسنة 2023 (التصالح في مخالفات البناء)",
            "law_name_en": "Law 187/2023 (Reconciliation on Violations)",
            "priority": 4,
            "can_be_suppressed": False,
        },
        {
            "filename": "fire_code_part1.pdf",
            "collection": "fire_code_part1",
            "law_name": "كود الحماية من الحريق - الجزء الأول",
            "law_name_en": "Egyptian Fire Code Part 1",
            "priority": 5,
            "can_be_suppressed": False,
        },
        {
            "filename": "parking_code.pdf",
            "collection": "parking_code",
            "law_name": "كود المواقف والجراجات",
            "law_name_en": "Parking/Garage Code",
            "priority": 5,
            "can_be_suppressed": False,
        },
        {
            "filename": "building_works_code_2005.pdf",
            "collection": "building_works_code_2005",
            "law_name": "كود أعمال البناء 2005",
            "law_name_en": "Building Works Code 2005",
            "priority": 5,
            "can_be_suppressed": False,
        },
        {
            "filename": "urban_planning_2021.pdf",
            "collection": "urban_planning_2021",
            "law_name": "اشتراطات التخطيط العمراني 2021",
            "law_name_en": "Urban Planning Conditions 2021",
            "priority": 6,
            "can_be_suppressed": True,  # Suppressed when Decree 943 or Law 119 covers same topic
        },
    ]


settings = Settings()
