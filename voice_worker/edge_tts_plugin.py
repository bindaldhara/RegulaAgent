"""Microsoft Edge TTS (no API key) for LiveKit Agents."""

from __future__ import annotations

import edge_tts
from livekit.agents import APIConnectOptions, tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

SAMPLE_RATE = 24000
NUM_CHANNELS = 1


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
        output_emitter.initialize(
            request_id="edge-tts",
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type="audio/mpeg",
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                output_emitter.push(chunk["data"])
        output_emitter.flush()
