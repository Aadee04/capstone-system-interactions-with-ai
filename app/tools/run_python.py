from langchain.tools import tool
import sys
import io

@tool("run_python") # return_direct=True) # Only return direct for tests
def run_python(code: str = ""):
    """Execute Python code and return the output or error. Input is the code to execute. Output is the result or error message."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        exec(code, {})
        output = sys.stdout.getvalue()
        error = sys.stderr.getvalue()
        return ("Success - " + output) if not error else ("Failure - " + error)
    except Exception as e:
        return f"Failure - {type(e).__name__}: {e}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
