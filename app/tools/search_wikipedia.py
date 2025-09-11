from langchain.tools import tool
try:
    import wikipedia
except ImportError:
    wikipedia = None

@tool("search_wikipedia")
def search_wikipedia(query: str = ""):
    """Search Wikipedia for a query and return a summary. Input is the term to be searched. Output is the summary or an error message."""
    if wikipedia is None:
        return "Wikipedia module not installed. Run 'pip install wikipedia'."
    try:
        return wikipedia.summary(query, sentences=2)
    except Exception as e:
        return f"Wikipedia search error: {e}"
