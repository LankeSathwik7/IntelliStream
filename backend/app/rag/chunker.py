"""Document chunking utilities."""

import re
from typing import Dict, List


class DocumentChunker:
    """Split documents into chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, title: str = "") -> List[Dict]:
        """
        Split text into overlapping chunks.

        Returns:
            List of chunk dicts with content and metadata
        """
        # Clean text
        text = self._clean_text(text)

        if len(text) <= self.chunk_size:
            return [{"content": text, "chunk_index": 0, "total_chunks": 1}]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within last 20% of chunk
                search_start = end - int(self.chunk_size * 0.2)
                sentence_end = self._find_sentence_end(text, search_start, end)
                if sentence_end > search_start:
                    end = sentence_end

            chunk_text = text[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({"content": chunk_text, "chunk_index": chunk_index})
                chunk_index += 1

            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        # Add total_chunks to each
        total = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove special characters that break embeddings
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        return text.strip()

    def _find_sentence_end(self, text: str, start: int, end: int) -> int:
        """Find the best sentence boundary in range."""
        # Look for sentence endings
        sentence_ends = [".", "!", "?", "\n"]
        best_pos = start

        for i in range(end - 1, start - 1, -1):
            if text[i] in sentence_ends:
                # Make sure it's not a decimal point
                if text[i] == "." and i + 1 < len(text) and text[i + 1].isdigit():
                    continue
                best_pos = i + 1
                break

        return best_pos


# Singleton instance
chunker = DocumentChunker()
