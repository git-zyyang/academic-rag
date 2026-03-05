"""
Smart Chunker — Structure-aware chunking for academic documents.
Supports section-aware splitting, paragraph boundaries, and configurable overlap.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from .config import CHUNKING_CONFIG


@dataclass
class Chunk:
    """Document chunk."""
    content: str
    chunk_index: int
    section_name: str = ""
    page_range: str = ""
    token_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.token_count:
            self.token_count = self._estimate_tokens(self.content)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count (Chinese ~1.5 chars/token, English ~1.3 words/token)."""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return int(chinese_chars * 1.5 + english_words * 1.3)


class AcademicChunker:
    """Structure-aware chunker for academic documents."""

    def __init__(self, doc_type: str = "academic_paper"):
        """
        Args:
            doc_type: Document type, maps to chunking config.
                      academic_paper | book_notes | policy_document | speech |
                      deep_read_note | reading_card | knowledge_index
        """
        self.config = CHUNKING_CONFIG.get(doc_type, CHUNKING_CONFIG["academic_paper"])
        self.chunk_size = self.config["chunk_size"]
        self.chunk_overlap = self.config["chunk_overlap"]
        self.separator = self.config["separator"]
        self.section_aware = self.config["section_aware"]

    def chunk_document(self, parsed_doc) -> list:
        """
        Chunk a parsed document.

        Args:
            parsed_doc: ParsedDocument from PDFParser

        Returns:
            list[Chunk]
        """
        if self.section_aware and parsed_doc.sections:
            return self._section_aware_chunk(parsed_doc)
        else:
            return self._simple_chunk(parsed_doc.full_text)

    def _section_aware_chunk(self, parsed_doc) -> list:
        """Section-aware chunking."""
        chunks = []
        chunk_index = 0

        for section_name, section_content in parsed_doc.sections:
            section_chunks = self._split_text(section_content)
            for text in section_chunks:
                if text.strip():
                    chunks.append(Chunk(
                        content=text.strip(),
                        chunk_index=chunk_index,
                        section_name=section_name,
                        metadata={
                            "source": parsed_doc.file_path,
                            "title": parsed_doc.title,
                            "authors": parsed_doc.authors,
                            "year": parsed_doc.year,
                            "language": parsed_doc.language,
                        }
                    ))
                    chunk_index += 1

        return chunks

    def _simple_chunk(self, text: str) -> list:
        """Simple chunking (when no section info available)."""
        chunks = []
        text_chunks = self._split_text(text)
        for i, chunk_text in enumerate(text_chunks):
            if chunk_text.strip():
                chunks.append(Chunk(
                    content=chunk_text.strip(),
                    chunk_index=i,
                ))
        return chunks

    def _split_text(self, text: str) -> list:
        """Split text into chunks according to config."""
        if not text or not text.strip():
            return []

        paragraphs = text.split(self.separator)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_long_paragraph(para)
                    chunks.extend(sub_chunks)
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _split_long_paragraph(self, text: str) -> list:
        """Split long paragraphs by sentence boundaries."""
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)
        chunks = []
        current = ""

        for sent in sentences:
            if len(current) + len(sent) <= self.chunk_size:
                current += sent
            else:
                if current:
                    chunks.append(current)
                current = sent

        if current:
            chunks.append(current)

        return chunks

    def _add_overlap(self, chunks: list) -> list:
        """Add overlap between adjacent chunks."""
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i-1][-self.chunk_overlap:]
            overlapped.append(prev_tail + "\n" + chunks[i])
        return overlapped


def chunk_document(parsed_doc, doc_type: str = "academic_paper") -> list:
    """Convenience function: chunk a parsed document."""
    chunker = AcademicChunker(doc_type)
    return chunker.chunk_document(parsed_doc)
