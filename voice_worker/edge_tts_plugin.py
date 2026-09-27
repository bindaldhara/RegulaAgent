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
_PCM_READ_BYTES = 8192


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
        # stream=False: one segment via push()+flush() (stream=True needs start_segment()).
        output_emitter.initialize(
            request_id="edge-tts",
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
            stream=False,
        )

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
            str(SAMPLE_RATE),
            "-ac",
            "1",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if proc.stdin is None or proc.stdout is None:
            raise RuntimeError("ffmpeg pipes unavailable")

        async def _feed_mpeg() -> None:
            try:
                communicate = edge_tts.Communicate(self.input_text, voice)
                async for chunk in communicate.stream():
                    if chunk["type"] != "audio":
                        continue
                    proc.stdin.write(chunk["data"])
                    await proc.stdin.drain()
            finally:
                proc.stdin.close()

        feed_task = asyncio.create_task(_feed_mpeg())
        pcm = bytearray()
        try:
            while True:
                block = await proc.stdout.read(_PCM_READ_BYTES)
                if not block:
                    break
                pcm.extend(block)
        finally:
            await feed_task
            rc = await proc.wait()
            if rc != 0 and proc.stderr is not None:
                err = (await proc.stderr.read()).decode(errors="replace")[:400]
                logger.error("ffmpeg mp3→pcm failed: %s", err)
                raise RuntimeError(f"ffmpeg mp3→pcm failed: {err}")

        if not pcm:
            raise RuntimeError("Edge TTS produced no audio")
        logger.info("Edge TTS pcm_bytes=%d text_chars=%d", len(pcm), len(self.input_text))
        output_emitter.push(bytes(pcm))
        output_emitter.flush()
