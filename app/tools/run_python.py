from langchain.tools import tool
import sys, io, ast, multiprocessing

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

def safe_exec(code: str, queue: multiprocessing.Queue):
    """Execute code in a restricted environment."""
    try:
        # AST check: disallow imports and exec statements
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Exec, ast.Call)):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec", "open", "__import__", "compile", "input"]:
                        raise ValueError(f"Use of '{node.func.id}' is not allowed")
                elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Exec)):
                    raise ValueError("Import or exec statements are not allowed")

        # Redirect stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        # Execute safely
        safe_globals = {"__builtins__": SAFE_BUILTINS}
        local_vars = {}
        exec(code, safe_globals, local_vars)

        output = sys.stdout.getvalue()
        error = sys.stderr.getvalue()
        result = output if not error else error

        queue.put(result)
    except Exception as e:
        queue.put(str(e))
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

@tool("run_python")
def run_python(code: str = "") -> str:
    """
    Safely execute Python code with restricted built-ins and no imports.
    Input: Python code (string)
    Output: Execution result or error message
    """
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=safe_exec, args=(code, queue))
    p.start()
    p.join(5)  # Timeout in seconds
    if p.is_alive():
        p.terminate()
        return "Execution timed out."
    return queue.get()
