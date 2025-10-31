import json
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
STORAGE_FILE = DATA_DIR / "storage_websites.json"

def load_storage():
    if STORAGE_FILE.exists():
        try:
            return json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_storage(websites):
    try:
        STORAGE_FILE.write_text(json.dumps(websites, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def add_website(url: str):
    if not url:
        return
    websites = load_storage()
    if url not in websites:
        websites.append(url)
        save_storage(websites)
