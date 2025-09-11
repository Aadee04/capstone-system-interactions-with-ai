import os, importlib
from langchain_core.tools import BaseTool

def discover_tools():
    tools = []
    for file in os.listdir("tools"):
        if file.endswith(".py") and file != "__init__.py":
            name = file[:-3]
            module = importlib.import_module(f"tools.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, BaseTool):  # safer than just checking attrs
                    tools.append(attr)
    return tools
