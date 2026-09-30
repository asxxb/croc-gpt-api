#!/usr/bin/env python3
"""Resolve the local Playwright profile path for the minimal ChatGPT API."""

from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILENAME = "profile_config.txt"
CONFIG_PATH = os.path.join(BASE_DIR, CONFIG_FILENAME)
DEFAULT_PROFILE_NAME = "chatgpt_profile"
ENV_VAR = "CHATGPT_PROFILE_PATH"


def _resolve(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return os.path.normpath(path)


def load_profile_path() -> str:
    env_value = os.environ.get(ENV_VAR, "").strip()
    if env_value:
        return _resolve(env_value)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            configured = handle.read().strip()
        if configured:
            return _resolve(configured)
    except OSError:
        pass

    return _resolve(DEFAULT_PROFILE_NAME)


def save_profile_path(profile_path: str) -> str:
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        handle.write(profile_path + "\n")
    return CONFIG_PATH
