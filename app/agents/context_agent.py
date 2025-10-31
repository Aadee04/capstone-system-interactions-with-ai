# /agents/context_agent.py

import re
from typing import Dict, Any
from app.context.context_manager import load_context, save_context, update_context, resolve_context

class ContextAgent:
    """
    Resolves user-specific phrases into actionable, system-understandable data.
    Auto-learns new mappings via user clarification.
    """

    def __init__(self):
        self.ctx = load_context()

    def identify_unknowns(self, query: str, known_mappings: Dict[str, Any]) -> list:
        """
        Detect potential placeholders or personal phrases not yet mapped.
        """
        tokens = re.findall(r"\bmy\s+\w+\b", query.lower())
        unknowns = []
        for token in tokens:
            key = token.replace("my ", "").strip()
            if key not in known_mappings and key not in self.ctx["persistent"]["folders"]:
                unknowns.append(key)
        return unknowns

    def clarify_and_learn(self, unknowns: list):
        """
        Ask user to define unknowns and store in persistent context.
        """
        for term in unknowns:
            value = input(f"[ContextAgent] I don't know what 'my {term}' refers to. Please specify the full path or meaning: ").strip()
            if not value:
                continue
            # Basic heuristic: if it looks like a file path, store as folder
            if "\\" in value or "/" in value:
                self.ctx["persistent"]["folders"][term] = value
            else:
                self.ctx["persistent"]["shortcuts"][term] = value
        save_context(self.ctx)

    def process(self, user_query: str) -> Dict[str, Any]:
        """
        Entry point for this agent. Returns resolved query and context info.
        """
        result = resolve_context(user_query)
        unknowns = self.identify_unknowns(user_query, result["mappings"])

        if unknowns:
            self.clarify_and_learn(unknowns)
            # Re-resolve after learning
            result = resolve_context(user_query)

        # Minimal AgentState-like structure
        state = {
            "user_query": user_query,
            "resolved_query": result["resolved"],
            "context_mappings": result["mappings"],
        }
        return state


if __name__ == "__main__":
    agent = ContextAgent()
    while True:
        q = input("\nEnter a query (or 'exit'): ").strip()
        if q.lower() == "exit":
            break
        output = agent.process(q)
        print("\n[Resolved Output]")
        print(output)
