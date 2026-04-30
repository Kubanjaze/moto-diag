"""Phase 191B — DiagnosticClient.ask_with_images() extension tests.

Mocks the Anthropic SDK ``client.messages.create`` call to inspect
the on-the-wire shape produced by ``ask_with_images``: image content
blocks (base64-encoded), tool/tool_choice threading, raw-Message
return type, and token-usage tracking.

Also includes a regression guard ensuring that the existing text-only
``ask()`` path still works after the extension lands (load-bearing
because Phase 191B's plan flags a "DiagnosticClient.ask_with_images()
extension may surface a latent bug in the existing text-only path"
risk).
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest import mock

import pytest

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import TokenUsage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(tmp_path: Path, name: str, content: bytes) -> Path:
    p = tmp_path / name
    p.write_bytes(content)
    return p


def _fake_message(
    *,
    text: str = "",
    tool_use_input: dict | None = None,
    input_tokens: int = 100,
    output_tokens: int = 200,
):
    """Fake Anthropic Message-shaped object."""

    class _Block:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    content_blocks = []
    if tool_use_input is not None:
        content_blocks.append(_Block(
            type="tool_use",
            name="report_video_findings",
            input=tool_use_input,
        ))
    if text:
        content_blocks.append(_Block(type="text", text=text))

    msg = mock.MagicMock()
    msg.content = content_blocks
    msg.usage = mock.MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    return msg


@pytest.fixture
def client():
    """DiagnosticClient with a fake API key (lazy-init avoids real SDK)."""
    return DiagnosticClient(api_key="sk-test-key-placeholder")


@pytest.fixture
def two_images(tmp_path):
    return [
        _make_image(tmp_path, "frame_001.jpg", b"\xff\xd8\xff\xe0fake1"),
        _make_image(tmp_path, "frame_002.jpg", b"\xff\xd8\xff\xe0fake2"),
    ]


# ---------------------------------------------------------------------------
# 1. Image content block construction
# ---------------------------------------------------------------------------


class TestImageContentBlocks:

    def test_builds_image_content_blocks_for_each_image(
        self, client, two_images,
    ):
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            sdk.messages.create.return_value = _fake_message(
                text="ok",
            )
            get_client.return_value = sdk

            client.ask_with_images(
                prompt="what do you see?",
                images=two_images,
            )

        # Inspect the SDK call.
        kwargs = sdk.messages.create.call_args.kwargs
        messages = kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        # 2 image blocks + 1 text block.
        assert len(content) == 3
        assert content[0]["type"] == "image"
        assert content[1]["type"] == "image"
        assert content[2]["type"] == "text"
        assert content[2]["text"] == "what do you see?"

    def test_image_blocks_use_base64_source(self, client, two_images):
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            sdk.messages.create.return_value = _fake_message(text="ok")
            get_client.return_value = sdk

            client.ask_with_images(
                prompt="x", images=two_images,
            )

        kwargs = sdk.messages.create.call_args.kwargs
        content = kwargs["messages"][0]["content"]
        for blk in content[:2]:
            assert blk["source"]["type"] == "base64"
            assert blk["source"]["media_type"] == "image/jpeg"
            # Round-trip the base64 → ensure it's our fixture bytes.
            decoded = base64.b64decode(blk["source"]["data"])
            assert decoded.startswith(b"\xff\xd8\xff\xe0fake")

    def test_image_blocks_match_input_order(
        self, client, two_images,
    ):
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            sdk.messages.create.return_value = _fake_message(text="ok")
            get_client.return_value = sdk

            client.ask_with_images(
                prompt="x", images=two_images,
            )

        kwargs = sdk.messages.create.call_args.kwargs
        content = kwargs["messages"][0]["content"]
        first_decoded = base64.b64decode(content[0]["source"]["data"])
        second_decoded = base64.b64decode(content[1]["source"]["data"])
        assert first_decoded == b"\xff\xd8\xff\xe0fake1"
        assert second_decoded == b"\xff\xd8\xff\xe0fake2"


# ---------------------------------------------------------------------------
# 2. Tool / tool_choice threading
# ---------------------------------------------------------------------------


class TestToolUseThreading:

    def test_tool_choice_threaded_through_when_provided(
        self, client, two_images,
    ):
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            sdk.messages.create.return_value = _fake_message(
                tool_use_input={"findings": []},
            )
            get_client.return_value = sdk

            tools = [{
                "name": "report_video_findings",
                "description": "report findings",
                "input_schema": {"type": "object"},
            }]
            tool_choice = {
                "type": "tool", "name": "report_video_findings",
            }
            client.ask_with_images(
                prompt="analyze",
                images=two_images,
                tools=tools,
                tool_choice=tool_choice,
            )

        kwargs = sdk.messages.create.call_args.kwargs
        assert kwargs["tools"] == tools
        assert kwargs["tool_choice"] == tool_choice

    def test_tools_kwarg_omitted_when_none(self, client, two_images):
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            sdk.messages.create.return_value = _fake_message(text="ok")
            get_client.return_value = sdk

            client.ask_with_images(
                prompt="x", images=two_images,
            )

        kwargs = sdk.messages.create.call_args.kwargs
        # When caller passed no tools, the SDK call should not include
        # them at all (passing tools=None changes SDK behavior).
        assert "tools" not in kwargs
        assert "tool_choice" not in kwargs


# ---------------------------------------------------------------------------
# 3. Return shape + token usage
# ---------------------------------------------------------------------------


class TestReturnShape:

    def test_returns_raw_message_not_text(self, client, two_images):
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            fake = _fake_message(
                tool_use_input={"findings": [{"x": 1}]},
            )
            sdk.messages.create.return_value = fake
            get_client.return_value = sdk

            result, usage = client.ask_with_images(
                prompt="x", images=two_images,
            )

        # The first return value is the raw Message — callers can
        # inspect content blocks for tool_use.
        assert result is fake
        assert isinstance(usage, TokenUsage)

    def test_records_token_usage(self, client, two_images):
        prior_count = client.session.call_count
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            sdk.messages.create.return_value = _fake_message(
                text="ok", input_tokens=100, output_tokens=200,
            )
            get_client.return_value = sdk

            _, usage = client.ask_with_images(
                prompt="x", images=two_images,
            )

        # Session metrics gained one entry.
        assert client.session.call_count == prior_count + 1
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200


# ---------------------------------------------------------------------------
# 4. Regression guard for existing ask() path
# ---------------------------------------------------------------------------


class TestExistingTextPathUnaffected:

    def test_ask_still_returns_text_after_image_extension(
        self, client,
    ):
        with mock.patch.object(
            client, "_get_client",
        ) as get_client:
            sdk = mock.MagicMock()
            sdk.messages.create.return_value = _fake_message(
                text="hello world",
            )
            get_client.return_value = sdk

            text, usage = client.ask(prompt="say hi")

        assert text == "hello world"
        assert isinstance(usage, TokenUsage)
        # ask() should NOT thread image content blocks.
        kwargs = sdk.messages.create.call_args.kwargs
        msg_content = kwargs["messages"][0]["content"]
        # Plain text content (string) — not a list of blocks.
        assert msg_content == "say hi"
