"""
app/models/embeddings.py
─────────────────────────
LANGCHAIN CONCEPT: Embeddings
──────────────────────────────
Embeddings convert text into vectors (lists of numbers).
Similar text → similar vectors → this is how semantic search works.

In code.teach, embeddings are used to:
  1. Store the student's uploaded notes in a vector store
  2. Store past tasks + outcomes so we can find similar ones
  3. Retrieve relevant chunks when generating a task grounded in their material

You only need ONE embedding model for the whole app.
We use Anthropic's embedding model via LangChain.

What you need to fill in:
  - Import the right embedding class
  - Instantiate the embedding model

Docs to read first:
  https://python.langchain.com/docs/integrations/text_embedding/
  (look for Anthropic or use OpenAI embeddings — both work the same interface)

Note: If Anthropic embeddings aren't available, use:
  from langchain_community.embeddings import HuggingFaceEmbeddings
  This runs locally, no API key needed — good for offline dev.
"""

from config import GOOGLE_API_KEY
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# ── Create the embeddings instance ──────────────────────────────────────────
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)


def get_embeddings():
    """
    Returns the shared embeddings model.
    """
    return embeddings

