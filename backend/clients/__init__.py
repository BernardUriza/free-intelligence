"""
Internal HTTP Clients - Free Intelligence

Clientes para llamar endpoints internos via HTTP.
"""

from .internal_llm_client import InternalLLMClient, get_llm_client

__all__ = ["InternalLLMClient", "get_llm_client"]
