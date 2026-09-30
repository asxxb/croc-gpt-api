# Croc GPT API

This is a smaller, separate project that keeps only the browser-profile flow.
It does not use the cookie-based path.

## What it includes

- `manual_login.py` to create and save a persistent ChatGPT browser profile
- `server.py` to expose a small local REST API
- `test_client.py` for a quick smoke test
- `profile_config.py` to resolve the profile location

## Setup

```bash
cd /Users/aseebshibin/Desktop/reverseapi/croc-gpt-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## First login

```bash
python3 manual_login.py
```

Log in to ChatGPT in the browser window, then press Enter in the terminal.

## Start the API

```bash
python3 server.py
```

## Test it

```bash
python3 test_client.py
```

## Endpoints

- `POST /chat` with `{ "prompt": "Hello" }`
- `POST /new-chat`
- `GET /health`
