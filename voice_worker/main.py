"""
LiveKit voice worker for RegulaAgent.

Committed user turns → POST /api/v1/agent/run → TTS reply.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    UserInputTranscribedEvent,
    cli,
    room_io,
)
from livekit.agents.llm import StopResponse
from livekit.plugins import silero

from audio_providers import build_stt_tts
from speech_text import text_for_tts

_root_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_root_env)
load_dotenv()

# Keep ONNX/VAD footprint down on Render free tier (512Mi).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regula-voice")
# Loop-monitor "event loop blocked" warnings are common on Render free tier during
# SSL/VAD/telemetry setup; they are not fatal. Keep Regula logs at INFO.
logging.getLogger("livekit.agents").setLevel(logging.WARNING)
VOICE_WORKER_BUILD = "2026-03-27-single-greeting"
CLIENT_AUDIO_WAIT_SEC = float(os.getenv("VOICE_CLIENT_AUDIO_WAIT_SEC", "20"))
GREETING_PLAYOUT_TIMEOUT_SEC = float(os.getenv("VOICE_GREETING_PLAYOUT_TIMEOUT_SEC", "45"))
_RENDER_HTTP_PORT = int(os.getenv("PORT", "8081"))

# LiveKit plugins must register on each process main thread before prewarm/job code runs.
from livekit.plugins import groq as _groq_plugin  # noqa: F401
REGULA_BACKEND_URL = os.getenv("REGULA_BACKEND_URL", "http://localhost:8000").rstrip("/")
DATA_TOPIC = "regula.agent"
VOICE_GREETING = (
    "Hey! I'm Regula, your assistant. How can I help you today?"
)
VOICE_FILLER = os.getenv("VOICE_FILLER", "One moment.")
VOICE_HISTORY_TURNS = int(os.getenv("VOICE_HISTORY_TURNS", "8"))
_HTTP_TIMEOUT = float(os.getenv("VOICE_HTTP_TIMEOUT", "60"))


def prewarm(proc: JobProcess) -> None:
    """Build STT/TTS once per worker process (avoids blocking the job event loop)."""
    proc.userdata["vad"] = silero.VAD.load()
    proc.userdata["stt"], proc.userdata["tts"] = build_stt_tts()


def _room_ready(room: rtc.Room) -> bool:
    return (
        room.connection_state == rtc.ConnectionState.CONN_CONNECTED
        and room.local_participant is not None
    )


async def _publish_data(room: rtc.Room, payload: dict[str, Any], *, reliable: bool = True) -> bool:
    if not _room_ready(room):
        return False
    body = json.dumps(payload).encode("utf-8")
    try:
        await room.local_participant.publish_data(
            body,
            reliable=reliable,
            topic=DATA_TOPIC,
        )
        return True
    except Exception as exc:
        logger.warning("publish_data failed (%s): %s", payload.get("type"), exc)
        return False


async def _publish_greeting_to_ui(room: rtc.Room) -> None:
    payload = {"type": "agent_greeting", "reply": VOICE_GREETING}
    for _ in range(24):
        if await _publish_data(room, payload):
            logger.info("agent_greeting sent to UI")
            return
        await asyncio.sleep(0.25)
    logger.warning("agent_greeting not delivered (room not ready)")


def _fire_say(session: AgentSession, text: str, **kwargs: Any) -> None:
    handle = session.say(text, **kwargs)
    if asyncio.iscoroutine(handle):
        asyncio.create_task(handle)


async def _play_opening_greeting(session: AgentSession, state: "RegulaSessionState") -> None:
    async with state._greeting_lock:
        if state._greeting_started:
            return
        state._greeting_started = True
    logger.info("Playing opening greeting (waiting for client speaker unlock)")
    state.bind_session(session)
    await _publish_greeting_to_ui(state.room)
    await state.wait_for_client_audio(timeout=CLIENT_AUDIO_WAIT_SEC)
    await state.speak_greeting(force=False)


async def _await_speech_playout(session: AgentSession, text: str, **kwargs: Any) -> None:
    handle = session.say(text, **kwargs)
    if asyncio.iscoroutine(handle):
        handle = await handle
    if handle is not None and hasattr(handle, "wait_for_playout"):
        await asyncio.wait_for(handle.wait_for_playout(), timeout=GREETING_PLAYOUT_TIMEOUT_SEC)


def _make_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=_HTTP_TIMEOUT,
        limits=httpx.Limits(max_keepalive_connections=4, max_connections=8),
    )


class RegulaSessionState:
    def __init__(
        self,
        session_meta: dict[str, Any],
        room: rtc.Room,
        http: httpx.AsyncClient,
    ) -> None:
        self.meta = session_meta
        self.room = room
        self._http = http
        self._busy = False
        self._session: AgentSession | None = None
        self._client_audio_ready = asyncio.Event()
        self._greeting_audio_done = False
        self._greeting_started = False
        self._greeting_lock = asyncio.Lock()
        self._greeting_speak_lock = asyncio.Lock()

    def bind_session(self, session: AgentSession) -> None:
        self._session = session

    def signal_client_audio(self) -> None:
        self._client_audio_ready.set()

    async def wait_for_client_audio(self, *, timeout: float) -> None:
        if self._client_audio_ready.is_set():
            return
        try:
            await asyncio.wait_for(self._client_audio_ready.wait(), timeout=timeout)
            logger.info("client speaker unlocked")
        except asyncio.TimeoutError:
            logger.warning("client speaker unlock timeout (%.0fs); speaking anyway", timeout)

    async def speak_greeting(self, *, force: bool) -> None:
        if self._greeting_audio_done and not force:
            return
        session = self._session
        if session is None:
            logger.warning("speak_greeting skipped: no session")
            return
        async with self._greeting_speak_lock:
            if self._greeting_audio_done and not force:
                return
            try:
                await _await_speech_playout(
                    session,
                    VOICE_GREETING,
                    allow_interruptions=False,
                )
                self._greeting_audio_done = True
                logger.info("Opening greeting playout finished")
            except asyncio.TimeoutError:
                logger.warning("Opening greeting playout timed out")
            except Exception:
                logger.exception("Opening greeting TTS failed")

    async def on_client_control(self, payload: dict[str, Any]) -> None:
        msg_type = payload.get("type")
        if msg_type == "client_audio_ready":
            self.signal_client_audio()
        elif msg_type == "replay_greeting" and self._session is not None and self._greeting_audio_done:
            await self.speak_greeting(force=True)

    def _http_client(self) -> httpx.AsyncClient:
        if self._http.is_closed:
            logger.warning("recreating closed Regula HTTP client")
            self._http = _make_http_client()
        return self._http

    async def on_transcript_ui(self, event: UserInputTranscribedEvent) -> None:
        text = (event.transcript or "").strip()
        if not text:
            return
        await _publish_data(
            self.room,
            {"type": "transcript", "text": text, "final": event.is_final},
            reliable=False,
        )

    async def on_committed_turn(self, session: AgentSession, text: str) -> None:
        text = text.strip()
        if not text or self._busy:
            return

        self._busy = True
        t0 = time.perf_counter()
        try:
            asyncio.create_task(
                _publish_data(
                    self.room,
                    {"type": "transcript", "text": text, "final": True},
                    reliable=False,
                )
            )
            if VOICE_FILLER:
                _fire_say(
                    session,
                    VOICE_FILLER,
                    allow_interruptions=True,
                    add_to_chat_ctx=False,
                )

            reply, run = await self._call_regula(text)
            api_ms = (time.perf_counter() - t0) * 1000
            spoken = text_for_tts(reply)

            turn_payload = {
                "type": "agent_turn",
                "user_message": text,
                "reply": reply,
                "run_id": run.get("run_id"),
                "conversation_id": run.get("conversation_id"),
                "policy": run.get("policy"),
                "intent": run.get("intent"),
                "current_step": run.get("current_step"),
                "proposed_action": run.get("proposed_action"),
                "tool_result": run.get("tool_result"),
                "identity_status": run.get("identity_status"),
                "consent_status": run.get("consent_status"),
            }

            async def _publish_turn() -> None:
                await _publish_data(self.room, turn_payload)

            await asyncio.gather(
                _publish_turn(),
                self._speak(session, spoken),
            )
            logger.info(
                "voice turn done api_ms=%.0f spoken_chars=%d total_ms=%.0f",
                api_ms,
                len(spoken),
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            logger.exception("voice turn failed: %s", exc)
            try:
                await self._speak(
                    session,
                    "Something went wrong while scheduling. Please try chat or try again.",
                    allow_interruptions=False,
                )
            except Exception:
                logger.debug("could not play error prompt after disconnect")
        finally:
            self._busy = False

    async def _speak(self, session: AgentSession, text: str, **kwargs: Any) -> None:
        say_opts = {"add_to_chat_ctx": True, "allow_interruptions": True}
        say_opts.update(kwargs)
        handle = session.say(text, **say_opts)
        if asyncio.iscoroutine(handle):
            handle = await handle
        if handle is not None and hasattr(handle, "wait_for_playout"):
            if os.getenv("VOICE_WAIT_PLAYOUT", "").lower() in ("1", "true", "yes"):
                await handle.wait_for_playout()

    async def _call_regula(self, user_message: str) -> tuple[str, dict[str, Any]]:
        access_token = self.meta.get("access_token")
        if not access_token:
            return (
                "Please sign in on the website before booking or canceling.",
                {},
            )

        history = list(self.meta.get("chat_history") or [])
        if VOICE_HISTORY_TURNS > 0:
            history = history[-VOICE_HISTORY_TURNS:]

        payload: dict[str, Any] = {
            "message": user_message,
            "chat_history": history,
            "voice_mode": True,
        }
        conversation_id = self.meta.get("conversation_id")
        if conversation_id:
            payload["conversation_id"] = conversation_id

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        client = self._http_client()
        response = await client.post(
            f"{REGULA_BACKEND_URL}/api/v1/agent/run",
            headers=headers,
            json=payload,
        )
        if response.status_code >= 400:
            logger.warning("Regula API %s: %s", response.status_code, response.text[:300])
            return (
                "I could not reach the scheduling service. Check that the API is running.",
                {},
            )
        data = response.json()

        reply = str(data.get("reply") or "Done.")
        new_conversation_id = data.get("conversation_id")
        if new_conversation_id:
            self.meta["conversation_id"] = new_conversation_id

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        self.meta["chat_history"] = history[-20:]
        return reply, data


class RegulaVoiceAgent(Agent):
    def __init__(self, state: RegulaSessionState) -> None:
        super().__init__(
            instructions="RegulaAgent voice scheduling. The server handles booking responses.",
        )
        self._state = state

    async def on_enter(self) -> None:
        await _play_opening_greeting(self.session, self._state)

    async def on_user_turn_completed(self, turn_ctx: Any, new_message: Any) -> None:
        text = (new_message.text_content or "").strip()
        if not text:
            raise StopResponse()
        await self._state.on_committed_turn(self.session, text)
        raise StopResponse()


# Render free tier = 512Mi RAM. Keep num_idle_processes=0 (no extra warm subprocesses).
# Do not use THREAD executor — Groq/STT plugins must register on the process main thread.
server = AgentServer(
    setup_fnc=prewarm,
    port=_RENDER_HTTP_PORT,
    num_idle_processes=0,
    load_threshold=0.99,
    initialize_process_timeout=120.0,
    job_memory_warn_mb=480,
    job_memory_limit_mb=0,
)


@server.rtc_session(agent_name=os.getenv("LIVEKIT_AGENT_NAME", "regula-voice"))
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}
    try:
        session_meta = json.loads(ctx.job.metadata or "{}")
    except json.JSONDecodeError:
        session_meta = {}

    stt = ctx.proc.userdata["stt"]
    tts = ctx.proc.userdata["tts"]
    vad = ctx.proc.userdata["vad"]

    agent_name = os.getenv("LIVEKIT_AGENT_NAME", "regula-voice")
    logger.info(
        "Regula voice worker joining room=%s agent_name=%s backend=%s build=%s",
        ctx.room.name,
        agent_name,
        REGULA_BACKEND_URL,
        VOICE_WORKER_BUILD,
    )

    http = await asyncio.to_thread(_make_http_client)
    state = RegulaSessionState(session_meta, ctx.room, http)

    async def _close_http() -> None:
        if not http.is_closed:
            await http.aclose()

    ctx.add_shutdown_callback(_close_http)

    session = AgentSession(
        vad=vad,
        stt=stt,
        tts=tts,
        llm=None,
    )

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(event: UserInputTranscribedEvent) -> None:
        asyncio.create_task(state.on_transcript_ui(event))

    @ctx.room.on("data_received")
    def _on_room_data(data: rtc.DataPacket) -> None:
        topic = getattr(data, "topic", None) or ""
        if topic and topic != DATA_TOPIC:
            return
        try:
            payload = json.loads(data.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        asyncio.create_task(state.on_client_control(payload))

    await ctx.connect()
    # Free-tier Render: cloud recording/OTEL setup blocks the agent loop for seconds.
    await session.start(
        agent=RegulaVoiceAgent(state),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            close_on_disconnect=False,
            delete_room_on_close=False,
        ),
        record=False,
    )


if __name__ == "__main__":
    # Render free tier: use dev worker settings (lighter than production start).
    on_render = os.getenv("RENDER", "").lower() in ("true", "1", "yes") or bool(
        os.getenv("RENDER_SERVICE_ID")
    )
    if on_render and len(sys.argv) >= 2 and sys.argv[1] == "start":
        sys.argv[1] = "dev"
    cli.run_app(server)
