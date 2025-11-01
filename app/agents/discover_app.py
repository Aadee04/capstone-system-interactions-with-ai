import os, importlib, inspect

# --- Dynamically discover tools in app/tools during each run ---
def discover_tools():
    tools = []
    for file in os.listdir("app/tools"):
        if file.endswith(".py") and file not in ["__init__.py"]:
            name = file[:-3]
            module = importlib.import_module(f"app.tools.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # Pick only callables that have `name` and `description` attributes
                if callable(attr) and hasattr(attr, "name") and hasattr(attr, "description"):
                    tools.append(attr)
    
    print(f"Discovered {len(tools)} tools: {[tool.name for tool in tools]}\n")
    return tools

def discover_tools_descriptions():
    tools_list = []
    for file in os.listdir("app/tools"):
        if file.endswith(".py") and file != "__init__.py":
            name = file[:-3]
            module = importlib.import_module(f"app.tools.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, "name") and hasattr(attr, "description"):
                    desc = attr.description.strip().split("\n")
                    tools_list.append((attr.name, desc))
    return tools_list



if __name__ == "__main__":
    print("Discover tools: ", discover_tools_descriptions())
    print("Total tools discovered: ", len(discover_tools()))
    print("-----")
    print("Tools with descriptions:", discover_tools_descriptions())