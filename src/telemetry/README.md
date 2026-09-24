# Optional active-machine counter

`server.py` is a small standard-library Python service. It accepts anonymous
`POST /check-in` requests with a 64-character hash derived from a machine ID,
and returns the number of distinct machines seen in the last 30 days through
`GET /count` with a private bearer token. It stores neither raw machine IDs nor
IP addresses. A machine checking many times counts once. An expired row changes
only the count; it does not affect that PC's installation.

The server binds to `127.0.0.1:8765`. Put it behind an HTTPS reverse proxy with
rate limits before setting its public URL in `src/data/telemetry.json`. Keep the
SQLite database and `RICE_COUNTER_ADMIN_TOKEN` outside the Git checkout. The
public client requires the user's opt-in in `~/.config/rice/telemetry.json`.
Without a configured HTTPS endpoint, it sends nothing.

Example local start:

```sh
RICE_COUNTER_DB="$HOME/.local/state/rice-counter.sqlite3" \
RICE_COUNTER_ADMIN_TOKEN='a-long-random-private-token' \
python3 src/telemetry/server.py
```

The maintainer's ignored `dev/admin.json` supplies the HTTPS URL and bearer
token to the local Dev Options window. Never add that file or a token to Git.
There is no way to use GitHub as an anonymous per-machine write API without
exposing a credential; hosting this service is required for a real count.
