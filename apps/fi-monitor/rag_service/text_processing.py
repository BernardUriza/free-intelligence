"""Text extraction and chunking utilities."""

from __future__ import annotations

import io
import re

from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes or plain text.

    Args:
        pdf_bytes: PDF file content or plain text as bytes

    Returns:
        Extracted text as string
    """
    # Try PDF extraction first
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)

        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

        return text.strip()
    except Exception:
        # If PDF parsing fails, assume it's plain text
        try:
            return pdf_bytes.decode('utf-8').strip()
        except Exception:
            # Last resort: try latin-1 encoding
            return pdf_bytes.decode('latin-1').strip()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into semantic chunks (paragraph-aware).

    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk in characters (soft limit)
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks (respects paragraph boundaries)
    """
    # Split by double newlines (paragraphs) first
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If paragraph fits in current chunk, add it
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            # Save current chunk if not empty
            if current_chunk:
                chunks.append(current_chunk.strip())

            # If paragraph itself is too large, split it by sentences
            if len(para) > chunk_size:
                sentences = para.replace('. ', '.|').replace('? ', '?|').replace('! ', '!|').split('|')
                temp_chunk = ""
                for sent in sentences:
                    if len(temp_chunk) + len(sent) <= chunk_size:
                        temp_chunk += sent + " "
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sent + " "
                if temp_chunk:
                    current_chunk = temp_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para + "\n\n"

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def preprocess_query(query: str) -> str:
    """Preprocess query to improve matching by removing filler words.

    Args:
        query: Raw user query

    Returns:
        Cleaned query with better semantic signal
    """
    # Remove Spanish question words (que, cual, como, etc.)
    query = re.sub(r'\b(qu\u00e9|cu\u00e1l|c\u00f3mo|d\u00f3nde|por qu\u00e9|cu\u00e1ndo|qui\u00e9n)\b', '', query, flags=re.IGNORECASE)

    # Remove "es la/el" filler (common in Spanish)
    query = re.sub(r'\bes (la|el|los|las)\b', '', query, flags=re.IGNORECASE)

    # Remove "son los/las" filler
    query = re.sub(r'\bson (los|las)\b', '', query, flags=re.IGNORECASE)

    # Remove multiple spaces
    query = re.sub(r'\s+', ' ', query)

    return query.strip()
