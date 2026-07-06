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

# ── TODO: Import loaders ──────────────────────────────────────────────────────
# from langchain_community.document_loaders import PyPDFLoader
# from langchain_community.document_loaders import WebBaseLoader
# from langchain_community.document_loaders import TextLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter


# ── TODO: Create the text splitter ───────────────────────────────────────────
# Use RecursiveCharacterTextSplitter with CHUNK_SIZE and CHUNK_OVERLAP from config
# This splitter tries to split on paragraphs first, then sentences, then words.
# It's the right default for most text.
#
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=CHUNK_SIZE,
#     chunk_overlap=CHUNK_OVERLAP
# )


def load_pdf(file_path: str):
    """
    Load a PDF and split it into chunks.
    
    TODO:
    1. Use PyPDFLoader(file_path) to load the PDF
    2. Call .load() to get a list of Document objects (one per page)
    3. Call text_splitter.split_documents(docs) to chunk them
    4. Return the list of chunks
    
    Each Document has:
      .page_content : str  — the text
      .metadata     : dict — {"source": "file.pdf", "page": 0}
    """
    pass


def load_url(url: str):
    """
    Load a webpage and split into chunks.
    
    TODO:
    1. Use WebBaseLoader([url]) to fetch the page
    2. .load() → list of Documents
    3. Split and return
    
    Good for: tutorial pages, documentation, Stack Overflow answers
    """
    pass


def load_text(text: str, source_name: str = "pasted_notes"):
    """
    Load plain text pasted directly by the student.
    
    TODO:
    1. Create a Document manually:
       from langchain_core.documents import Document
       doc = Document(page_content=text, metadata={"source": source_name})
    2. Split and return
    """
    pass


def load_material(source: str, source_type: str = "auto"):
    """
    Smart loader — detects type and routes to the right loader.
    
    TODO:
    - if source_type == "pdf"  or source ends with .pdf → load_pdf()
    - if source_type == "url"  or source starts with http → load_url()
    - else → load_text()
    
    This is the only function the rest of the app calls.
    """
    pass
