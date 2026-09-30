#!/usr/bin/env python3
"""Minimal local ChatGPT REST API using a persistent browser profile."""

from __future__ import annotations

import atexit
import json
import os
import time

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from profile_config import load_profile_path


app = Flask(__name__)
CORS(app)

_playwright = None
_context = None
_page = None
_startup_error = None


def _model_payload():
    return {
        "object": "list",
        "data": [
            {
                "id": "chatgpt-local",
                "object": "model",
                "created": 0,
                "owned_by": "local",
            }
        ],
    }


def _cleanup() -> None:
    global _context, _playwright
    for closer in (_context.close if _context else None, _playwright.stop if _playwright else None):
        try:
            if closer:
                closer()
        except Exception:
            pass


atexit.register(_cleanup)


def _find_input():
    if _page is None:
        raise RuntimeError("Browser is not initialized")

    selectors = [
        'textarea[placeholder*="Message"]',
        'textarea[placeholder*="message"]',
        'textarea',
        'div[contenteditable="true"]',
    ]

    for selector in selectors:
        locator = _page.locator(selector)
        if locator.count() and locator.first.is_visible():
            return locator.first

    raise RuntimeError("Could not find the ChatGPT input box")


def _assistant_count() -> int:
    if _page is None:
        return 0
    return _page.locator('[data-message-author-role="assistant"]').count()


def _last_assistant_text() -> str:
    if _page is None:
        raise RuntimeError("Browser is not initialized")

    messages = _page.locator('[data-message-author-role="assistant"]')
    count = messages.count()
    if count == 0:
        raise RuntimeError("No assistant response found")

    for index in range(count - 1, -1, -1):
        text = messages.nth(index).evaluate("node => (node.textContent || '').trim()")
        if isinstance(text, str) and text.strip():
            return text.strip()

    raise RuntimeError("No assistant response text found")


def _wait_for_assistant_text(before_count: int, timeout_seconds: int = 180) -> str:
    if _page is None:
        raise RuntimeError("Browser is not initialized")

    deadline = time.time() + timeout_seconds
    last_text = ""
    stable_hits = 0

    while time.time() < deadline:
        try:
            current_text = _last_assistant_text()
        except Exception:
            time.sleep(0.5)
            continue

        if current_text:
            if current_text == last_text:
                stable_hits += 1
            else:
                last_text = current_text
                stable_hits = 0

            if stable_hits >= 2 and _assistant_count() > before_count:
                return current_text

        time.sleep(1)

    if last_text:
        return last_text
    raise PlaywrightTimeoutError("Timed out waiting for assistant response text")


def _start_browser() -> None:
    global _playwright, _context, _page, _startup_error

    profile_path = load_profile_path()
    if not os.path.exists(profile_path):
        _startup_error = f"Profile not found at {profile_path}. Run: python3 manual_login.py"
        return

    try:
        _playwright = sync_playwright().start()
        _context = _playwright.chromium.launch_persistent_context(
            profile_path,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        _page = _context.pages[0] if _context.pages else _context.new_page()
        _page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
        time.sleep(2)
        _find_input()
    except Exception as exc:
        _startup_error = f"Browser failed to start: {exc}"
        _cleanup()


def _send_prompt(prompt: str) -> str:
    if _page is None:
        raise RuntimeError("Browser is not initialized")

    textbox = _find_input()
    before = _assistant_count()

    textbox.click()
    textbox.fill(prompt)
    textbox.press("Enter")

    try:
        _page.wait_for_function(
            """(count) => document.querySelectorAll('[data-message-author-role="assistant"]').length > count""",
            arg=before,
            timeout=180000,
        )
    except PlaywrightTimeoutError:
        pass

    return _wait_for_assistant_text(before)


def _chat_completion_payload(prompt: str, response_text: str, model: str) -> dict:
    now = int(time.time())
    return {
        "id": f"chatcmpl-{now}",
        "object": "chat.completion",
        "created": now,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(prompt),
            "completion_tokens": len(response_text),
            "total_tokens": len(prompt) + len(response_text),
        },
    }


def _stream_chat_completion(prompt: str, response_text: str, model: str):
    now = int(time.time())
    stream_id = f"chatcmpl-{now}"

    def generate():
        first_chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": now,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": response_text},
                    "finish_reason": None,
                }
            ],
        }
        final_chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": now,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }

        yield f"data: {json.dumps(first_chunk)}\n\n"
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/health")
def health():
    if _startup_error:
        return jsonify({"ready": False, "error": _startup_error}), 503
    return jsonify({"ready": _page is not None, "error": None}), 200


@app.get("/models")
@app.get("/v1/models")
@app.get("/chat/models")
@app.get("/chat/v1/models")
@app.get("/v1/chat/completions/models")
@app.get("/v1/chat/completions/v1/models")
def models():
    return jsonify(_model_payload()), 200


@app.get("/v1/chat/completions")
def chat_completions_schema():
    return jsonify(
        {
            "object": "endpoint",
            "message": "Use POST /chat with {\"prompt\": \"...\"} or POST /v1/chat/completions with OpenAI-style payloads.",
        }
    ), 200


@app.post("/chat")
def chat():
    if _startup_error:
        return jsonify({"success": False, "error": _startup_error}), 503

    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"success": False, "error": "prompt must be a non-empty string"}), 400

    try:
        response_text = _send_prompt(prompt.strip())
        return jsonify({"success": True, "response": response_text, "prompt": prompt.strip()}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.post("/v1/chat/completions")
def openai_chat_completions():
    if _startup_error:
        return jsonify({"error": _startup_error}), 503

    data = request.get_json(silent=True) or {}
    stream = bool(data.get("stream", False))
    messages = data.get("messages", [])
    prompt = ""
    model = data.get("model", "chatgpt-local")
    if isinstance(messages, list):
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "user":
                content = message.get("content", "")
                if isinstance(content, str):
                    prompt = content.strip()
                    break

    if not prompt:
        return jsonify({"error": "messages must include a user message"}), 400

    try:
        response_text = _send_prompt(prompt)
        if stream:
            return _stream_chat_completion(prompt, response_text, model)

        return jsonify(_chat_completion_payload(prompt, response_text, model)), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/responses")
@app.post("/v1/responses")
def openai_responses():
    if _startup_error:
        return jsonify({"error": _startup_error}), 503

    data = request.get_json(silent=True) or {}

    prompt = ""
    input_value = data.get("input")

    if isinstance(input_value, str):
        prompt = input_value.strip()
    elif isinstance(input_value, list):
        for item in reversed(input_value):
            if isinstance(item, str) and item.strip():
                prompt = item.strip()
                break
            if isinstance(item, dict):
                if item.get("type") == "input_text" and isinstance(item.get("text"), str):
                    prompt = item["text"].strip()
                    break
                if item.get("role") == "user":
                    content = item.get("content", "")
                    if isinstance(content, str) and content.strip():
                        prompt = content.strip()
                        break

    if not prompt and isinstance(data.get("messages"), list):
        for message in reversed(data["messages"]):
            if isinstance(message, dict) and message.get("role") == "user":
                content = message.get("content", "")
                if isinstance(content, str) and content.strip():
                    prompt = content.strip()
                    break

    if not prompt:
        return jsonify({"error": "input must contain text to send"}), 400

    try:
        response_text = _send_prompt(prompt)
        return jsonify(
            {
                "id": f"resp-{int(time.time())}",
                "object": "response",
                "created_at": int(time.time()),
                "model": data.get("model", "chatgpt-local"),
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "id": f"msg-{int(time.time())}",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": response_text,
                            }
                        ],
                    }
                ],
                "output_text": response_text,
                "usage": {
                    "input_tokens": len(prompt),
                    "output_tokens": len(response_text),
                    "total_tokens": len(prompt) + len(response_text),
                },
            }
        ), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/chat/completions")
def chat_completions_legacy():
    return openai_chat_completions()


@app.post("/chat/chat/completions")
def chat_chat_completions_legacy():
    return openai_chat_completions()


@app.post("/new-chat")
def new_chat():
    if _startup_error:
        return jsonify({"success": False, "error": _startup_error}), 503

    try:
        _page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
        time.sleep(2)
        _find_input()
        return jsonify({"success": True, "message": "New chat started"}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


def main() -> int:
    _start_browser()
    if _startup_error:
        print(_startup_error)
        return 1

    print("Minimal ChatGPT API running on http://localhost:5001")
    print("Endpoints: POST /chat, POST /new-chat, GET /health")
    try:
        app.run(host="0.0.0.0", port=5001, debug=False, threaded=False)
    finally:
        _cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
