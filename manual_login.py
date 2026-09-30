#!/usr/bin/env python3
"""Open a persistent Chrome profile and let you log in once."""

from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import sync_playwright

from profile_config import ENV_VAR, load_profile_path, save_profile_path


def main() -> int:
    if len(sys.argv) > 1:
        os.environ[ENV_VAR] = sys.argv[1]

    profile_path = load_profile_path()
    os.makedirs(profile_path, exist_ok=True)
    save_profile_path(profile_path)

    print("=" * 60)
    print("Minimal ChatGPT API login")
    print("=" * 60)
    print(f"Profile: {profile_path}")
    print("A browser window will open. Log in to ChatGPT, then press Enter here.")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            profile_path,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://chatgpt.com/", wait_until="domcontentloaded")

        try:
            if sys.stdin.isatty():
                input("Press Enter when the chat UI is ready... ")
            else:
                print("Non-interactive terminal detected; waiting 120 seconds.")
                time.sleep(120)
        except (KeyboardInterrupt, EOFError):
            pass

        context.close()

    print("Saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
