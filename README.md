## Setup

```bash
uv venv
uv sync
```

## Run

```bash
cp settings.yaml.example settings.yaml
```

Set up in `settings.yaml`:

- your staff email, Omnidesk domain, and Omnidesk api key
- your JWT token for InNoHassle Accounts (get it from [here](https://api.innohassle.ru/accounts/v0/docs#/Tokens/generate_service_token_tokens_generate_service_token_get))

```bash
uv run uvicorn src.api.app:app --reload
```

Test UI

```bash
uv run python -m http.server 8001
```

Open http://localhost:8001
(you can get your Innohassle JWT from [here](https://innohassle.ru/account/token))

P.S. One-shot (vibecoded) by Sonnet 4.6, not inclined to write this glue by myself.
