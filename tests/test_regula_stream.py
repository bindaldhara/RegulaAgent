import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "voice_worker"))

from regula_stream import _parse_sse_data, _dispatch_sse


def test_parse_sse_data_joins_multiline() -> None:
    data = _parse_sse_data(['{"text": "Hello"}'])
    assert data == {"text": "Hello"}


def test_dispatch_sse_token() -> None:
    parts: list[str] = []
    collected: list[str] = []

    async def on_token(text: str) -> None:
        collected.append(text)

    asyncio.run(
        _dispatch_sse(
            "token",
            {"text": "Hello "},
            on_status=None,
            on_step=None,
            on_token=on_token,
            reply_parts=parts,
        )
    )
    assert parts == ["Hello "]
    assert collected == ["Hello "]


def test_dispatch_sse_done() -> None:
    parts: list[str] = []
    done = asyncio.run(
        _dispatch_sse(
            "done",
            {"reply": "Hi", "run_id": "abc"},
            on_status=None,
            on_step=None,
            on_token=None,
            reply_parts=parts,
        )
    )
    assert done == {"reply": "Hi", "run_id": "abc"}
