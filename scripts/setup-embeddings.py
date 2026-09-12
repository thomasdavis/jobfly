"""Download the local text encoder once, before starting the offline service."""
import os
from fastembed import TextEmbedding

path = os.environ["JOBFLY_EMBED_CACHE"]
TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2", cache_dir=path, threads=1)
print(f"Embedding model ready in {path}")
