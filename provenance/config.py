import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "provenance.db"
APP_TITLE = "PROVENANCE"
CHROMA_PATH = os.getenv("CHROMA_PERSIST_DIRECTORY", str(ROOT_DIR / ".chroma"))

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
    or os.getenv("LLM_API_KEY")
    or os.getenv("OPENAI_API_KEY")
)
if LLM_API_KEY in {"replace-with-your-google-ai-studio-key", "replace-with-your-key", "change-me"}:
    LLM_API_KEY = None
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-flash-latest")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
