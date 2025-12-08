"""
RAG (Retrieval Augmented Generation) service for document embeddings and retrieval.
"""

import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from django.conf import settings

from api.models import Collection, CollectionItem

logger = logging.getLogger(__name__)


class RAGService:
    """Service for managing RAG collections and querying documents."""

    def __init__(self, collection: Collection):
        self.collection = collection
        self._setup_client()

    def _setup_client(self):
        """Initialize the embedding client based on provider."""
        if self.collection.embedding_provider == Collection.EmbeddingProvider.GEMINI:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.embedding_model = f"models/{self.collection.embedding_model}"
            self.completion_model = self.collection.completion_model
        else:
            raise NotImplementedError(f"Provider {self.collection.embedding_provider} not yet implemented")

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks based on collection's chunking strategy."""
        if self.collection.chunking_strategy == Collection.ChunkingStrategy.NO_CHUNKING:
            return [text]

        chunk_length = self.collection.chunk_length or 1000
        chunk_overlap = self.collection.chunk_overlap or 0

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_length
            chunk = text[start:end]
            chunks.append(chunk)

            if self.collection.chunking_strategy == Collection.ChunkingStrategy.WINDOW:
                start = end - chunk_overlap
            else:  # FIXED_LENGTH
                start = end

        return chunks

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using configured provider."""
        try:
            if self.collection.embedding_provider == Collection.EmbeddingProvider.GEMINI:
                # Try with output_dimensionality first (newer API)
                try:
                    result = genai.embed_content(
                        model=self.embedding_model,
                        content=text,
                        task_type="retrieval_document",
                        output_dimensionality=self.collection.embedding_dimensions,
                    )
                except TypeError:
                    # Fallback for older API without output_dimensionality
                    result = genai.embed_content(
                        model=self.embedding_model,
                        content=text,
                        task_type="retrieval_document",
                    )
                return result["embedding"]
            else:
                raise NotImplementedError(f"Provider {self.collection.embedding_provider} not implemented")
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def add_document(
        self, name: str, content: str, description: str = "", metadata: Optional[Dict] = None
    ) -> CollectionItem:
        """Add a document to the collection with embeddings."""
        # chunks = self._chunk_text(content)

        # For now, store the full content with a single embedding
        # In production, you'd want to store chunks separately
        embedding = self._generate_embedding(content)

        item = CollectionItem.objects.create(
            collection=self.collection,
            name=name,
            description=description,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
        )

        logger.info(f"Added document '{name}' to collection '{self.collection.name}'")
        return item

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query the collection and return most relevant documents."""
        # Generate query embedding
        query_embedding = self._generate_embedding(query_text)

        # Get all items with embeddings
        items = CollectionItem.objects.filter(collection=self.collection, embedding__isnull=False)

        # Calculate similarities
        results = []
        for item in items:
            if item.embedding:
                similarity = self._cosine_similarity(query_embedding, item.embedding)
                results.append(
                    {
                        "item": item,
                        "similarity": similarity,
                        "content": item.content,
                        "name": item.name,
                        "metadata": item.metadata,
                    }
                )

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def generate_answer(self, query_text: str, context_docs: List[Dict[str, Any]]) -> str:
        """Generate an answer using retrieved documents as context."""
        # Build context from retrieved documents
        context = "\n\n".join([f"Document: {doc['name']}\n{doc['content']}" for doc in context_docs])

        prompt = f"""Based on the following documents, answer the question.

Context:
{context}

Question: {query_text}

Answer:"""

        try:
            model = genai.GenerativeModel(self.completion_model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"Error generating answer: {str(e)}"

    def query_and_answer(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        """Query collection and generate an answer based on retrieved documents."""
        # Retrieve relevant documents
        results = self.query(query_text, top_k=top_k)

        if not results:
            return {"status": "error", "message": "No relevant documents found", "answer": None, "sources": []}

        # Generate answer
        answer = self.generate_answer(query_text, results)

        return {
            "status": "success",
            "answer": answer,
            "sources": [
                {"name": r["name"], "similarity": r["similarity"], "content": r["content"][:200] + "..."}
                for r in results
            ],
        }
