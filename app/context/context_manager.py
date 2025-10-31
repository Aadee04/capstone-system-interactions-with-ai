import json
import os
import re
from typing import Dict, Any

CONTEXT_DIR = "data/context"
CONTEXT_FILE = os.path.join(CONTEXT_DIR, "user_context.json")

# --- Default Context Structure ---

DEFAULT_CONTEXT = {
    "persistent": {
        "folders": {
            "work": "C:/Users/USER/Documents/Work",
            "school": "C:/Users/USER/Documents/School",
        },
        "shortcuts": {
            "browser": "chrome.exe",
            "editor": "code.exe",
        },
        "workflows": {
            "daily_startup": ["open chrome.exe", "open code.exe"],
            "coding_setup": ["open code.exe", "open terminal"],
        },
        "sessions": {
            "last_session": [],
        },
    },
    "dynamic": {
        "recent_files": [],
        "open_apps": [],
        "clipboard": "",
        "last_action": "",
    },
}

# --- Synonym Mapping for Robustness ---

SYNONYMS = {
    "school": ["study", "college", "education"],
    "work": ["office", "job", "workplace"],
    "browser": ["chrome", "edge", "firefox", "internet"],
    "editor": ["vscode", "code", "notepad++"],
    "folder": ["directory", "path", "drive"],
    "open": ["launch", "start", "run"],
}

# --- Core IO Operations ---

def ensure_context_dir():
    if not os.path.exists(CONTEXT_DIR):
        os.makedirs(CONTEXT_DIR)

def load_context() -> Dict[str, Any]:
    """Load user context, fallback to defaults if missing or invalid."""
    ensure_context_dir()
    if not os.path.exists(CONTEXT_FILE):
        save_context(DEFAULT_CONTEXT)
        return DEFAULT_CONTEXT.copy()
    try:
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ("persistent", "dynamic"):
            data.setdefault(key, DEFAULT_CONTEXT[key])
        return data
    except Exception as e:
        print(f"[Context Manager] Failed to load context: {e}")
        return DEFAULT_CONTEXT.copy()

def save_context(data: Dict[str, Any]):
    """Save updated context to disk."""
    ensure_context_dir()
    try:
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Context Manager] Save failed: {e}")

# --- Context Operations ---

def normalize_query(text: str) -> str:
    """Lowercase and strip punctuation for consistent matching."""
    return re.sub(r"[^\w\s]", "", text.lower().strip())

def update_context(section: str, key: str, value: Any):
    """Update a context field and persist."""
    ctx = load_context()
    if section not in ctx:
        print(f"[Context Manager] Unknown section: {section}")
        return
    ctx[section][key] = value
    save_context(ctx)

def find_match(word: str, mapping: Dict[str, Any]) -> str | None:
    """Find a key match via synonyms."""
    normalized = normalize_query(word)
    for canonical, synonyms in SYNONYMS.items():
        if normalized == canonical or normalized in synonyms:
            for ctx_key in mapping.keys():
                if canonical in ctx_key or ctx_key in synonyms:
                    return ctx_key
    for ctx_key in mapping.keys():
        if normalized in ctx_key:
            return ctx_key
    return None

def resolve_context(query: str) -> Dict[str, Any]:
    """
    Resolve user query using persistent and dynamic mappings.
    Expands flexible phrases like "my school folder" or "open my editor".
    """
    ctx = load_context()
    resolved_query = query
    found = {}
    qnorm = normalize_query(query)

    # Search folders
    for name, path in ctx["persistent"]["folders"].items():
        if re.search(rf"\b(my )?{name}\b", qnorm):
            resolved_query = re.sub(rf"\b(my )?{name}\b", path, resolved_query, flags=re.I)
            found[name] = path
        else:
            match = find_match(name, ctx["persistent"]["folders"])
            if match and re.search(match, qnorm):
                resolved_query = re.sub(match, path, resolved_query, flags=re.I)
                found[match] = path

    # Search shortcuts / apps
    for alias, exe in ctx["persistent"]["shortcuts"].items():
        if re.search(rf"\b(my )?{alias}\b", qnorm):
            resolved_query = re.sub(rf"\b(my )?{alias}\b", exe, resolved_query, flags=re.I)
            found[alias] = exe
        else:
            match = find_match(alias, ctx["persistent"]["shortcuts"])
            if match and re.search(match, qnorm):
                resolved_query = re.sub(match, exe, resolved_query, flags=re.I)
                found[match] = exe

    # Search workflows
    for wf_name, steps in ctx["persistent"].get("workflows", {}).items():
        if re.search(rf"\b(run|start|execute) (my )?{wf_name}\b", qnorm):
            found[wf_name] = steps
            resolved_query += f" [Workflow Detected: {wf_name}]"

    # Dynamic state (recent files, open apps)
    if "recent" in qnorm:
        found["recent_files"] = ctx["dynamic"]["recent_files"]
    if "open apps" in qnorm or "running" in qnorm:
        found["open_apps"] = ctx["dynamic"]["open_apps"]

    return {
        "original": query,
        "resolved": resolved_query.strip(),
        "mappings": found,
    }
