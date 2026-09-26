"""Prepare API replies for TTS (strip markdown, keep speakable length)."""

from __future__ import annotations

import os
import re

_MAX_TTS_CHARS = int(os.getenv("VOICE_TTS_MAX_CHARS", "1200"))


def text_for_tts(reply: str) -> str:
    text = reply.strip()
    if not text:
        return "Done."
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)
    text = text.replace("\n\n", ". ")
    text = text.replace("\n", ". ")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > _MAX_TTS_CHARS:
        cut = text[: _MAX_TTS_CHARS - 48].rsplit(" ", 1)[0]
        text = f"{cut}. For the full details, check the chat."
    return text
