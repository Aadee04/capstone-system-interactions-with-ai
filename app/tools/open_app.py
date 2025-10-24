from langchain.tools import tool
import os

# -------------- Define allowed OS apps --------------
ALLOWED_OS_ACTIONS = {
    "calculator": ["calc.exe"],            # Calculator
    "word": [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],  # adjust path
    "notepad": ["notepad.exe"],
}
# ----------------------------------------------------


def run_safe_os_command(app_name: str):
    """Launch a whitelisted app."""
    if app_name.lower() not in ALLOWED_OS_ACTIONS:
        return f"Success - Launching '{app_name}' is not allowed."
    try:
        path = ALLOWED_OS_ACTIONS[app_name.lower()]
        for p in path:
            os.startfile(p)
        return f"Success - {app_name} opened successfully."
    except Exception as e:
        return f"Failure - Could not open {app_name}: {e}"


@tool("open_app")
def open_app(app_name: str = "") -> str:
    """Safely open a desktop application if whitelisted. Currently supports: calculator, word, notepad."""
    return run_safe_os_command(app_name)
