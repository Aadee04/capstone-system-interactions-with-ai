import os
import numpy as np
from sentence_transformers import SentenceTransformer
from app.agents.discover_app import discover_tools_descriptions

def generate_tool_embeddings(save_dir: str = "data/embeddings"):
    os.makedirs(save_dir, exist_ok=True)

    # 1. Load model
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    # 2. Prepare corpus
    tools = discover_tools_descriptions()
    tool_texts = [f"{name}: {desc}" for name, desc in tools]
    # tool_texts = [f"{name.replace('_', ' ')}: {desc}" for name, desc in tools]

    # 3. Generate embeddings
    tool_embeddings = embedder.encode(tool_texts, normalize_embeddings=True)

    # 4. Save
    np.save(os.path.join(save_dir, "tool_embeddings.npy"), tool_embeddings)
    with open(os.path.join(save_dir, "tool_texts.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(tool_texts))

    print(f"Saved {len(tool_texts)} tool embeddings to {save_dir}")

if __name__ == "__main__":
    generate_tool_embeddings()
