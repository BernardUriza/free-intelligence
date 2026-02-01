"""
Ground Truth Annotation Generation

Hybrid approach:
1. LLM generates questions for each chunk (Ollama llama3.1:8b)
2. User validates critical cases manually
3. Store annotations with relevance scores (3=highly, 2=medium, 1=marginal)

Annotations enable RAG quality evaluation via Recall, Precision, MRR, NDCG metrics.
"""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def call_ollama_llm(
    prompt: str,
    model: str = "llama3.1:8b",
    timeout: float = 30.0,
    ollama_url: str = "http://localhost:11434",
) -> str:
    """
    Call Ollama LLM API for text generation.

    Args:
        prompt: Input text prompt
        model: Ollama model name (default: llama3.1:8b)
        timeout: Request timeout in seconds
        ollama_url: Ollama API base URL

    Returns:
        Generated text response

    Raises:
        httpx.ConnectError: Ollama service not running
        httpx.TimeoutException: Request timeout
        httpx.HTTPStatusError: Non-200 response
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,  # Get full response at once
            },
        )
        response.raise_for_status()

        data = response.json()
        return data["response"]


async def generate_questions_for_chunk(
    chunk_text: str,
    questions_per_chunk: int = 2,
    model: str = "llama3.1:8b",
) -> list[str]:
    """
    Generate medical questions that a chunk directly answers.

    Uses Ollama LLM with medical-context prompt engineering.

    Args:
        chunk_text: PDF text chunk to analyze
        questions_per_chunk: Number of questions to generate
        model: Ollama model to use

    Returns:
        List of generated questions (empty if chunk has no usable info)

    Example:
        chunk = "Normal blood sugar: 70-100 mg/dL fasting. HbA1c <5.7% is normal."
        questions = await generate_questions_for_chunk(chunk)
        # Returns: [
        #   "What is the normal fasting blood sugar range?",
        #   "What HbA1c level indicates normal glucose control?"
        # ]
    """
    # Medical-context prompt
    prompt = f"""You are a medical information expert. Given this medical text chunk:

"{chunk_text}"

Generate {questions_per_chunk} clear medical questions that this chunk DIRECTLY answers with specific information.

CRITICAL RULES:
- ONLY generate questions if the chunk contains explicit medical facts, numbers, or recommendations
- Questions must be answerable by ONLY this chunk (not require outside knowledge)
- Use medical terminology appropriately
- Return ONLY a JSON array of strings, nothing else

Example format: ["What is the hypertension dosage?", "What are side effects?"]

If the chunk has no specific medical information (e.g., just headers, page numbers, disclaimers), return: []

Generated questions:"""

    response_text = ""
    try:
        response_text = await call_ollama_llm(prompt, model=model)

        # Extract JSON array from response
        # LLM might wrap in ```json ... ``` or add text before/after
        response_text = response_text.strip()

        # Remove markdown code fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Find first line with [ and last with ]
            start_idx = next(
                (i for i, line in enumerate(lines) if "[" in line), None
            )
            end_idx = next(
                (
                    len(lines) - 1 - i
                    for i, line in enumerate(reversed(lines))
                    if "]" in line
                ),
                None,
            )
            if start_idx is not None and end_idx is not None:
                response_text = "\n".join(lines[start_idx : end_idx + 1])

        # Parse JSON
        questions = json.loads(response_text)

        if not isinstance(questions, list):
            logger.warning(
                f"LLM returned non-list: {type(questions)}. Using empty list."
            )
            return []

        # Validate all elements are strings
        questions = [q for q in questions if isinstance(q, str) and q.strip()]

        logger.info(
            f"Generated {len(questions)} questions for chunk ({len(chunk_text)} chars)"
        )
        return questions[:questions_per_chunk]  # Limit to requested count

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.debug(f"Raw response: {response_text}")
        return []
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.error(f"Ollama API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating questions: {e}")
        return []


async def generate_annotations_for_document(
    filename: str,
    chunks: list[str],
    questions_per_chunk: int = 2,
    model: str = "llama3.1:8b",
) -> list[dict[str, Any]]:
    """
    Generate ground truth annotations for all chunks in a document.

    Batch processes chunks sequentially to avoid VRAM exhaustion.

    Args:
        filename: Document filename (for logging)
        chunks: List of text chunks from PDF
        questions_per_chunk: Number of questions per chunk
        model: Ollama model to use

    Returns:
        List of annotation dicts:
        [
            {
                "query": "What is normal blood sugar?",
                "relevant_chunks": [5],  # Chunk index that answers this
                "relevance_scores": [3],  # 3=highly relevant
                "source": "llm_generated",
                "validated": False
            },
            ...
        ]

    Example:
        chunks = ["Text 1", "Text 2", ...]
        annotations = await generate_annotations_for_document(
            "diabetes.pdf", chunks, questions_per_chunk=2
        )
        # Returns ~20 annotations (10 chunks × 2 questions each)
    """
    annotations = []

    logger.info(
        f"Generating annotations for {filename}: {len(chunks)} chunks, "
        f"{questions_per_chunk} questions/chunk"
    )

    for chunk_idx, chunk_text in enumerate(chunks):
        try:
            questions = await generate_questions_for_chunk(
                chunk_text, questions_per_chunk=questions_per_chunk, model=model
            )

            for question in questions:
                # Each question is relevant to exactly this chunk
                # Default relevance: 3 (highly relevant) since LLM confirmed
                # chunk DIRECTLY answers the question
                annotations.append(
                    {
                        "query": question,
                        "relevant_chunks": [chunk_idx],
                        "relevance_scores": [3],  # Highly relevant
                        "source": "llm_generated",
                        "validated": False,  # User hasn't reviewed yet
                    }
                )

            logger.debug(
                f"Chunk {chunk_idx}/{len(chunks)}: {len(questions)} questions generated"
            )

        except Exception as e:
            logger.error(f"Failed to generate annotations for chunk {chunk_idx}: {e}")
            # Continue with next chunk (don't fail entire batch)
            continue

    logger.info(
        f"Generated {len(annotations)} total annotations for {filename} "
        f"({len(annotations)/len(chunks):.1f} avg per chunk)"
    )

    return annotations
