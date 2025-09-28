from langchain.tools import tool
import sys
import io
import threading

# Safe built-ins
SAFE_BUILTINS = {
    "range": range,
    "len": len,
    "print": print,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "min": min,
    "max": max,
    "sum": sum,
}

@tool("run_python")
def run_python(code: str = "") -> str:
    """
    Safely execute Python code with restricted built-ins and no imports.
    Input: Python code (string)
    Output: Execution result or error message
    """

    output = {"result": ""}

    def exec_code():
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            exec(code, {"__builtins__": SAFE_BUILTINS})
            out = sys.stdout.getvalue()
            err = sys.stderr.getvalue()
            output["result"] = out if not err else err
        except Exception as e:
            output["result"] = str(e)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    thread = threading.Thread(target=exec_code)
    thread.start()
    thread.join(timeout=10)
    if thread.is_alive():
        return "Execution timed out."
    return output["result"]
