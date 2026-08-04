"""RAG pipeline contracts."""

from chartmaster.data.external_documents import ExternalDocument


def chunk_documents(documents: list[ExternalDocument]) -> list[dict]:
    """Split raw documents into retrievable chunks."""
    raise NotImplementedError("Add chunking when external document collection starts.")


def build_vector_index(chunks: list[dict]) -> object:
    """Build or update a vector index for external factor retrieval."""
    raise NotImplementedError("Select a vector store before implementing this.")


def summarize_external_factors(symbol: str, query: str) -> str:
    """Retrieve context and summarize external factors for one symbol."""
    raise NotImplementedError("Implement after vector index storage is selected.")

