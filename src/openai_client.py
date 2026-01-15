"""Shared OpenAI client helpers for the SANS web app."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def create_chat_completion(
    *,
    api_key: str,
    model: str,
    messages: Iterable[dict[str, str]],
    max_tokens: int,
) -> Any:
    """
    Create a chat completion via OpenAI.

    Args:
        api_key: OpenAI API key
        model: OpenAI model name
        messages: Chat messages payload
        max_tokens: Maximum tokens to generate

    Returns:
        OpenAI response object
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    return client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=list(messages),
    )
