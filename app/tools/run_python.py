from langchain.tools import tool
import sys
import io

@tool("run_python")
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
        return output if not error else error
    except Exception as e:
        return str(e)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
