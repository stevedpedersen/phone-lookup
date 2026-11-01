# Phone Lookup

Check a phone number against different sites / twilio. Most sites have a paywall, but basic info can still be obtained.

## Install & run

```zsh
uv venv && source .venv/bin/activate && uv sync

# Interactive cli
uv run lookup

# With a number argument in any format
uv run lookup 555-555-1234
```

Lists the URLs – cmd/ctrl + click to open. Add new sites by editing `src/phone_lookup/sites.json`.

Twilio integration requires you set env vars:

```zsh
TWILIO_ACCOUNT_SID=<sid>
TWILIO_AUTH_TOKEN=<token>
```

