"""Microsoft Edge TTS (no API key) for LiveKit Agents."""

from __future__ import annotations

import asyncio
import logging

import edge_tts
from livekit.agents import APIConnectOptions, tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

logger = logging.getLogger("regula-voice.tts")

SAMPLE_RATE = 24000
NUM_CHANNELS = 1


async def _mpeg_bytes_to_pcm(mpeg: bytes, sample_rate: int) -> bytes:
    """Decode Edge MP3 to raw s16le PCM (LiveKit plays PCM reliably; MP3 mid-stream is flaky on small CPUs)."""
    if not mpeg:
        return b""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=mpeg)
    if proc.returncode != 0:
        detail = (stderr or b"").decode(errors="replace")[:400]
        raise RuntimeError(f"ffmpeg mp3→pcm failed: {detail}")
    return stdout


class EdgeTTS(tts.TTS):
    def __init__(self, *, voice: str = "en-US-JennyNeural") -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._voice = voice

    @property
    def model(self) -> str:
        return "edge-tts"

    @property
    def provider(self) -> str:
        return "edge.microsoft.com"

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> tts.ChunkedStream:
        return _EdgeChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class _EdgeChunkedStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        voice = self._tts._voice  # type: ignore[attr-defined]
        communicate = edge_tts.Communicate(self.input_text, voice)
        mpeg = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mpeg.extend(chunk["data"])
        try:
            pcm = await _mpeg_bytes_to_pcm(bytes(mpeg), SAMPLE_RATE)
        except Exception as exc:
            logger.exception("Edge TTS decode failed: %s", exc)
            raise
        output_emitter.initialize(
            request_id="edge-tts",
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
        )
        output_emitter.push(pcm)
        output_emitter.flush()
