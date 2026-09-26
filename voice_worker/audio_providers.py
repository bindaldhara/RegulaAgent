"""Resolve STT/TTS for voice worker."""

from __future__ import annotations

import os
from typing import Any

from edge_tts_plugin import EdgeTTS


def _is_openrouter_key(value: str | None) -> bool:
    return bool(value and value.strip().startswith("sk-or-"))


def _livekit_inference_available() -> bool:
    return bool(
        os.getenv("LIVEKIT_URL", "").strip()
        and os.getenv("LIVEKIT_API_KEY", "").strip()
        and os.getenv("LIVEKIT_API_SECRET", "").strip()
    )


def _build_free() -> tuple[Any, Any]:
    """
    Free stack (default):
    - STT: Groq Whisper (free tier at https://console.groq.com)
    - TTS: Microsoft Edge TTS (no API key)
    """
    from livekit.plugins import groq

    groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not groq_key:
        raise RuntimeError(
            "Free voice STT needs GROQ_API_KEY (free at https://console.groq.com). "
            "TTS uses Edge and needs no key."
        )

    stt = groq.STT(
        model=os.getenv("VOICE_GROQ_STT_MODEL", "whisper-large-v3-turbo"),
        api_key=groq_key,
    )
    tts = EdgeTTS(voice=os.getenv("VOICE_EDGE_TTS_VOICE", "en-US-JennyNeural"))
    return stt, tts


def build_stt_tts() -> tuple[Any, Any]:
    mode = os.getenv("VOICE_AUDIO_MODE", "free").lower()

    if mode == "free":
        return _build_free()

    from livekit.plugins import openai

    voice_openai = (os.getenv("VOICE_OPENAI_API_KEY") or "").strip()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    openrouter_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    openrouter_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

    effective_openai = voice_openai or (
        openai_key if openai_key and not _is_openrouter_key(openai_key) else ""
    )

    if mode == "openai" and effective_openai:
        return (
            openai.STT(model="whisper-1", api_key=effective_openai, use_realtime=False),
            openai.TTS(voice=os.getenv("VOICE_OPENAI_TTS_VOICE", "ash"), api_key=effective_openai),
        )

    if mode == "openrouter" and (openrouter_key or _is_openrouter_key(openai_key)):
        or_key = openrouter_key or openai_key
        stt = openai.STT(
            model=os.getenv("VOICE_OPENROUTER_STT_MODEL", "openai/whisper-large-v3"),
            api_key=or_key,
            base_url=openrouter_base,
            use_realtime=False,
        )
        if voice_openai:
            tts = openai.TTS(
                voice=os.getenv("VOICE_OPENAI_TTS_VOICE", "ash"),
                api_key=voice_openai,
            )
            return stt, tts
        if _livekit_inference_available():
            from livekit.agents import inference

            tts = inference.TTS(
                os.getenv("VOICE_LIVEKIT_TTS_MODEL", "cartesia/sonic-3"),
                voice=os.getenv(
                    "VOICE_LIVEKIT_TTS_VOICE",
                    "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
                ),
            )
            return stt, tts
        return stt, EdgeTTS(voice=os.getenv("VOICE_EDGE_TTS_VOICE", "en-US-JennyNeural"))

    if mode == "livekit" and _livekit_inference_available():
        from livekit.agents import inference

        return (
            inference.STT(
                os.getenv("VOICE_LIVEKIT_STT_MODEL", "deepgram/nova-3"),
                language=os.getenv("VOICE_LIVEKIT_STT_LANGUAGE", "en"),
            ),
            inference.TTS(
                os.getenv("VOICE_LIVEKIT_TTS_MODEL", "cartesia/sonic-3"),
                voice=os.getenv(
                    "VOICE_LIVEKIT_TTS_VOICE",
                    "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
                ),
            ),
        )

    # Unknown mode or missing creds → free stack
    return _build_free()
