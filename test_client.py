#!/usr/bin/env python3
"""Small client for the minimal ChatGPT API."""

from __future__ import annotations

import sys

import requests

BASE_URL = "http://localhost:5001"


def main() -> int:
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Say hello in 3 words."

    health = requests.get(f"{BASE_URL}/health", timeout=10)
    print("health:", health.json())

    response = requests.post(f"{BASE_URL}/chat", json={"prompt": prompt}, timeout=180)
    print(response.json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
