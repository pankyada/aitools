"""Chat command handler."""

from __future__ import annotations

import sys
from pathlib import Path

from ait_core.config.settings import AITSettings

from ait_xai.client import XAIClient
from ait_xai.models import ChatMessage, ChatRequest


def resolve_prompt(prompt: str | None, prompt_file: Path | None, use_stdin: bool) -> str:
    """Resolve a prompt from direct text, file, or stdin.

    Args:
        prompt: Direct prompt text.
        prompt_file: Optional prompt file path.
        use_stdin: Whether to read from stdin.

    Returns:
        Resolved prompt string.

    Raises:
        ValueError: If no prompt source was provided.
        OSError: If prompt file read fails.
    """

    if prompt:
        return prompt
    if prompt_file:
        return prompt_file.read_text(encoding="utf-8")
    if use_stdin:
        data = sys.stdin.read()
        return data.strip()
    raise ValueError("Provide one of --prompt, --prompt-file, or --stdin")


async def run_chat(
    settings: AITSettings,
    prompt: str,
    system: str | None,
    model: str | None,
    temperature: float,
    max_tokens: int | None,
    stream: bool,
    json_mode: bool,
) -> dict[str, object]:
    """Execute a single-turn chat completion.

    Args:
        settings: Loaded settings.
        prompt: User prompt text.
        system: Optional system instruction.
        model: Optional model override.
        temperature: Sampling temperature.
        max_tokens: Optional token limit.
        stream: Stream flag forwarded to API.
        json_mode: Whether to request JSON-formatted outputs.

    Returns:
        Chat payload with model, content, and finish reason.

    Raises:
        ToolsetError: If API call fails.
    """

    client = XAIClient(settings=settings)
    messages: list[ChatMessage] = []
    if system:
        messages.append(ChatMessage(role="system", content=system))
    messages.append(ChatMessage(role="user", content=prompt))

    request = ChatRequest(
        model=model or settings.xai.default_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        response_format={"type": "json_object"} if json_mode else None,
    )
    result = await client.chat(request)
    return result.model_dump(exclude_none=True)


async def run_chat_interactive(
    settings: AITSettings,
    system: str | None,
    model: str | None,
    temperature: float,
    max_tokens: int | None,
) -> dict[str, object]:
    """Execute interactive multi-turn chat session.

    Args:
        settings: Loaded settings.
        system: Optional system prompt.
        model: Optional model override.
        temperature: Sampling temperature.
        max_tokens: Optional token limit.

    Returns:
        Session transcript payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = XAIClient(settings=settings)
    messages: list[ChatMessage] = []
    if system:
        messages.append(ChatMessage(role="system", content=system))

    transcript: list[dict[str, str]] = []
    while True:
        user_text = input("you> ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break

        messages.append(ChatMessage(role="user", content=user_text))
        request = ChatRequest(
            model=model or settings.xai.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        result = await client.chat(request)
        messages.append(ChatMessage(role="assistant", content=result.content))

        transcript.append({"role": "user", "content": user_text})
        transcript.append({"role": "assistant", "content": result.content})
        print(f"assistant> {result.content}")

    return {"transcript": transcript, "turns": len(transcript) // 2}
