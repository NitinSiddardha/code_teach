"""
app/retrieval/loader.py
────────────────────────
LANGCHAIN CONCEPT: Document Loaders + Text Splitters
──────────────────────────────────────────────────────
Document Loaders read files (PDFs, URLs, text) and return LangChain Document objects.
Text Splitters break those documents into chunks small enough for embedding.

Why chunking matters:
  - Embeddings work best on short, focused pieces of text (~200-500 chars)
  - A whole PDF as one chunk loses all semantic structure
  - Chunk overlap (50 chars) prevents concepts from being split mid-sentence

In code.teach, we support:
  1. PDF upload (student's lecture notes, textbooks)
  2. URL (student pastes a tutorial link)
  3. Plain text (student pastes notes directly)

After loading + splitting, the chunks go into the vector store (vector_store.py).

Docs to read:
  https://python.langchain.com/docs/concepts/document_loaders
  https://python.langchain.com/docs/concepts/text_splitters
"""

from config import CHUNK_SIZE, CHUNK_OVERLAP
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)


def load_pdf(file_path: str):
    """
    Load a PDF and split it into chunks.
    """
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    return text_splitter.split_documents(docs)


def load_url(url: str):
    """
    Load a webpage and split into chunks.
    """
    loader = WebBaseLoader(url)
    docs = loader.load()
    return text_splitter.split_documents(docs)


def load_text(text: str, source_name: str = "pasted_notes"):
    """
    Load plain text pasted directly by the student.
    """
    doc = Document(page_content=text, metadata={"source": source_name})
    return text_splitter.split_documents([doc])


def load_material(source: str, source_type: str = "auto"):
    """
    Smart loader — detects type and routes to the right loader.
    """
    normalized = source.strip()
    if source_type == "pdf" or normalized.lower().endswith(".pdf"):
        return load_pdf(normalized)
    if source_type == "url" or normalized.lower().startswith("http"):
        return load_url(normalized)
    return load_text(source, source_name=source_type or "pasted_notes")
