from langchain.tools import tool
import webbrowser

@tool("open_browser_and_search", return_direct=True)
def open_browser_and_search(url: str = ""):
    """Open a site in the default web browser. 
    Input is the URL to be searched. Output is the opened site"""
    webbrowser.open(url)
    return f"Success - Opened {url}"
