<!-- <p align="center">
  <img src="logo.png" alt="Croc GPT API Logo" width="200"/>
</p> -->

# Croc GPT API

This is a smaller, separate project that keeps only the browser-profile flow.
It does not use the cookie-based path.

CROC-GPT-API acts as a bridge between your authenticated browser session and your AI coding agent. It exposes an OpenAI-compatible endpoint so you can use it for connection to Claude Code, Hermes, etc. by choosing a custom endpoint as your coding agent.

- **Zero Cost**: Uses your existing web subscription credits.
- **Session Preservation**: Keeps your web session alive via cookie management.


![Croc GPT API Demo](demo.gif)

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

- Wait for the chromium browser to automatically open.
- Log in to ChatGPT in the opened chromium browser using email or password/social-login.
- Then press Enter in the terminal.

## Start the API

```bash
python3 server.py
```

an  openai complatible endpoint will be running on `http://[IP_ADDRESS]/` .
use the end point to connect with claude code, Hermes , VS code  or any other tool/agent that supports openai compatible end points.𓆌


## Addon


```bash
curl --request POST \
  --url http://[IP_ADDRESS]/chat \
  --header 'accept: application/json' \
  --header 'Content-Type: application/json' \
  --data '{
	"prompt": "write a fastapi server for a webapp "
}'
```

## Test it

```bash
python3 test_client.py
```

## Endpoints

- `POST /chat` with `{ "prompt": "Hello 𓆌" }`
- `POST /new-chat`
- `GET /health`

