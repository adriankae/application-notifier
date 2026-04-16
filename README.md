# application-notifier

`application-notifier` is a small host-scheduled reminder runner for the eczema tracking stack.

It does three things:

1. queries the `Eczema-Tracker` backend for due items
2. resolves subject and location names deterministically
3. hands a structured reminder payload to the existing OpenClaw Telegram path

The important constraint for v1 is that the notifier does not talk to Telegram directly.
OpenClaw remains responsible for the final wording and delivery through the existing bot/chat loop.

## Architecture

```text
host systemd timer
  -> host oneshot service
      -> docker exec <openclaw-container> python /app/application-notifier/run_reminder.py --slot morning|evening
          -> backend query + resolution + slot filtering
          -> structured reminder payload
          -> OpenClaw bridge command
          -> existing OpenClaw bot/chat loop
          -> Telegram delivery
```

### Slot semantics

- Morning: notify for all due items
- Evening: notify only for due items where `current_phase_number == 1`

### What lives where

- Backend owns the truth about subjects, locations, episodes, and due logic
- Notifier owns querying, slot filtering, grouping, locking, logging, and bridge invocation
- OpenClaw owns user-facing wording and Telegram delivery

## Repo Layout

```text
application-notifier/
├─ README.md
├─ pyproject.toml
├─ .env.example
├─ install.sh
├─ run_reminder.py
├─ deploy/
│  └─ systemd/
│     ├─ application-notifier-morning.service
│     ├─ application-notifier-morning.timer
│     ├─ application-notifier-evening.service
│     └─ application-notifier-evening.timer
├─ src/
│  └─ application_notifier/
│     ├─ __init__.py
│     ├─ cli.py
│     ├─ config.py
│     ├─ czm_config.py
│     ├─ backend_client.py
│     ├─ resolver.py
│     ├─ selector.py
│     ├─ openclaw_bridge.py
│     ├─ payload_builder.py
│     ├─ fallback_renderer.py
│     ├─ orchestration.py
│     └─ models.py
└─ tests/
   ├─ test_selector.py
   ├─ test_fallback_renderer.py
   ├─ test_config_resolution.py
   └─ test_payload_builder.py
```

## Installation

### 1. Edit the environment file

Start from [.env.example](/Users/dhnkjc7/Documents/application-notifier/.env.example) and set:

- `CZM_API_KEY`
- `OPENCLAW_CONTAINER_NAME`
- `OPENCLAW_BRIDGE_COMMAND`

The bridge command should be the existing OpenClaw-side command or wrapper that knows how to send a message through the configured Telegram bot/chat loop.

### 2. Run the installer

```bash
./install.sh
```

The installer will:

- verify `docker` exists
- check the target OpenClaw container
- sync the notifier code into the container
- write systemd unit files
- install or print the exact `sudo` commands needed for system-level deployment
- enable the timers
- perform a dry-run check

## Configuration

### Backend config resolution

The notifier resolves backend config in this order:

1. explicit env vars
2. existing `czm` config file
3. fail with a clear error

Supported env vars:

- `CZM_BASE_URL`
- `CZM_API_KEY`
- `CZM_TIMEZONE`
- `CZM_CONFIG_PATH`

The `czm` config file uses the same TOML shape as `czm-cli`:

```toml
base_url = "http://localhost:28173"
api_key = "plaintext-api-key-from-the-backend"
timezone = "Europe/Berlin"
```

### OpenClaw bridge config

Supported env vars:

- `OPENCLAW_BRIDGE_MODE`
- `OPENCLAW_BRIDGE_COMMAND`
- `OPENCLAW_BRIDGE_FALLBACK_COMMAND`
- `OPENCLAW_BRIDGE_TARGET`
- `OPENCLAW_BRIDGE_TIMEOUT_SECONDS`

The bridge command is expected to run inside the existing OpenClaw container and to consume the payload from the environment or from the temp files the notifier passes in.

Example:

```env
OPENCLAW_BRIDGE_COMMAND=sh -lc 'exec openclaw message send --channel telegram --target "your-chat-or-username" --message "$APPLICATION_NOTIFIER_MESSAGE_TEXT"'
```

The notifier exposes these payload variables to the bridge process:

- `APPLICATION_NOTIFIER_PAYLOAD_FILE`
- `APPLICATION_NOTIFIER_FALLBACK_FILE`
- `APPLICATION_NOTIFIER_PAYLOAD_JSON`
- `APPLICATION_NOTIFIER_MESSAGE_TEXT`
- `APPLICATION_NOTIFIER_SLOT`
- `APPLICATION_NOTIFIER_TIMEZONE`
- `APPLICATION_NOTIFIER_BRIDGE_TARGET`

## Usage

Run directly:

```bash
python -m application_notifier.cli --slot morning
python -m application_notifier.cli --slot evening
```

Dry-run:

```bash
python -m application_notifier.cli --slot morning --dry-run
python -m application_notifier.cli --slot evening --print-only
```

Force fallback rendering:

```bash
python -m application_notifier.cli --slot morning --force-fallback
```

## Systemd

The repo ships host-level systemd templates in `deploy/systemd/`.

Useful commands:

```bash
systemctl status application-notifier-morning.timer
journalctl -u application-notifier-morning.service -n 100 --no-pager
systemctl start application-notifier-morning.service
```

Timer schedules:

- morning: 08:00
- evening: 20:00
- `Persistent=true` is enabled for both timers

## Manual testing

### Dry-run in the container

```bash
docker exec <openclaw-container> python /app/application-notifier/run_reminder.py --slot morning --dry-run
docker exec <openclaw-container> python /app/application-notifier/run_reminder.py --slot evening --dry-run
```

### Real run

```bash
docker exec <openclaw-container> python /app/application-notifier/run_reminder.py --slot morning
docker exec <openclaw-container> python /app/application-notifier/run_reminder.py --slot evening
```

### Container debugging

```bash
docker exec -it <openclaw-container> sh
env | grep -E 'CZM_|OPENCLAW_|APPLICATION_NOTIFIER_'
python /app/application-notifier/run_reminder.py --slot morning --print-only
```

## Locking

The notifier uses a single file lock so overlapping timer runs exit cleanly without sending duplicate reminders.

## Security notes

- The notifier never calls the Telegram Bot API directly
- The notifier never calls a raw LLM provider directly for the final user-facing reminder
- API keys stay in the existing `czm` config path or in env vars
- The bridge command should be constrained to the existing OpenClaw container/runtime

## Troubleshooting

If a timer fires but nothing is sent:

1. check the host unit logs
2. check the container stderr/stdout for the bridge command
3. verify `CZM_API_KEY` or the `czm` config file exists inside the container
4. verify `OPENCLAW_BRIDGE_COMMAND` points at a real OpenClaw-side send path

Example log commands:

```bash
journalctl -u application-notifier-morning.service -n 100 --no-pager
journalctl -u application-notifier-evening.service -n 100 --no-pager
```

## Future v2 ideas

- per-subject reminder formatting
- delivery acknowledgements
- richer bridge health checks
- better OpenClaw runtime detection
- optional preview mode for multiple chat targets
