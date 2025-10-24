from langchain.tools import tool

try:
    import wikipedia
    from wikipedia.exceptions import DisambiguationError, PageError
except ImportError:
    wikipedia = None

@tool("search_wikipedia")
def search_wikipedia(query: str = ""):
    """Search Wikipedia for a query and return a summary. 
    The query must be as unambiguous as possible (specify category)"""
    if wikipedia is None:
        return "Wikipedia module not installed. Run 'pip install wikipedia'."
    
    if not query or not isinstance(query, str) or not query.strip():
        return "Please provide a search term to search on Wikipedia."

    try:
        return wikipedia.summary(query, sentences=2)
    except DisambiguationError as e:
        # Suggest first few options
        options = e.options[:5] if hasattr(e, "options") else []
        return f"Disambiguation error. Did you mean: {', '.join(options)}?"
    except PageError:
        return f"No Wikipedia page found for '{query}'."
    except Exception as e:
        return f"Wikipedia search error: {e}"
