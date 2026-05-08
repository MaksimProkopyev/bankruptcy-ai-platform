"""
Token-aware chunking for legal texts.
"""

import re
from typing import List, Optional
from dataclasses import dataclass

from rag.config import config


@dataclass
class Chunk:
    """A text chunk with metadata."""
    text: str
    start_pos: int
    end_pos: int
    token_count: int
    metadata: dict


class LegalChunker:
    """Chunker that respects sentence boundaries and token limits."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        self.sentence_endings = r'[.!?;]\s+'

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token for Russian)."""
        return len(text) // 4

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(self.sentence_endings, text)
        # Remove empty strings
        return [s.strip() for s in sentences if s.strip()]

    def chunk(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """Split text into overlapping chunks."""
        sentences = self.split_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_token_count = 0
        start_pos = 0

        for i, sentence in enumerate(sentences):
            sent_tokens = self.estimate_tokens(sentence)
            if current_token_count + sent_tokens > self.chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = " ".join(current_chunk)
                end_pos = start_pos + len(chunk_text)
                chunks.append(Chunk(
                    text=chunk_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    token_count=current_token_count,
                    metadata=(metadata or {}).copy()
                ))
                # Start new chunk with overlap
                overlap_tokens = 0
                overlap_sentences = []
                for j in range(len(current_chunk) - 1, -1, -1):
                    overlap_tokens += self.estimate_tokens(current_chunk[j])
                    if overlap_tokens > self.chunk_overlap:
                        break
                    overlap_sentences.insert(0, current_chunk[j])
                current_chunk = overlap_sentences
                current_token_count = overlap_tokens
                start_pos = end_pos - len(" ".join(overlap_sentences))
            current_chunk.append(sentence)
            current_token_count += sent_tokens

        # Add last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            end_pos = start_pos + len(chunk_text)
            chunks.append(Chunk(
                text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos,
                token_count=current_token_count,
                metadata=(metadata or {}).copy()
            ))

        return chunks