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
      -> docker exec <openclaw-container> python3 /app/application-notifier/run_reminder.py --slot morning|evening
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
- `OPENCLAW_PYTHON_BIN` if the container does not expose `python3`

The bridge command should be the existing OpenClaw-side command or wrapper that knows how to send a message through the configured Telegram bot/chat loop.

### 2. Prepare as the normal user

```bash
./install.sh
```

The prepare step will:

- verify `docker` exists
- check the target OpenClaw container
- sync the notifier code into the container
- write a generated env file at `./.generated/application-notifier.env`
- perform a dry-run check
- print the exact root-only next step

### 3. Install systemd as root

```bash
sudo ./install.sh install-systemd
```

The root-only step will:

- install the env file to `/etc/application-notifier/application-notifier.env`
- install the systemd service and timer units to `/etc/systemd/system`
- reload systemd
- enable the morning and evening timers

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
- `OPENCLAW_PYTHON_BIN`
- `OPENCLAW_REMINDER_STYLE_GUIDE`
- `OPENCLAW_REMINDER_STYLE_FILE`

The bridge command is expected to run inside the existing OpenClaw container and to consume the payload and instructions from the environment or from the temp files the notifier passes in.

The notifier now sends OpenClaw a structured factual payload plus a compact instruction block. OpenClaw is expected to turn that into the final human-sounding reminder and send it through the existing Telegram bot/chat loop.

Example:

```env
OPENCLAW_BRIDGE_COMMAND="/app/application-notifier/deploy/openclaw-reminder-wrapper.sh"
OPENCLAW_REMINDER_COMPOSE_COMMAND="your-actual-openclaw-compose-entrypoint"
OPENCLAW_REMINDER_STYLE_GUIDE="Warm, human, and lightly conversational. Avoid sounding robotic or repetitive."
```

The notifier exposes these payload variables to the bridge process:

- `APPLICATION_NOTIFIER_PAYLOAD_FILE`
- `APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS_FILE`
- `APPLICATION_NOTIFIER_FALLBACK_FILE`
- `APPLICATION_NOTIFIER_PAYLOAD_JSON`
- `APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS`
- `APPLICATION_NOTIFIER_MESSAGE_TEXT` when `OPENCLAW_BRIDGE_FALLBACK_COMMAND` is used or `--force-fallback` is set
- `APPLICATION_NOTIFIER_SLOT`
- `APPLICATION_NOTIFIER_TIMEZONE`
- `APPLICATION_NOTIFIER_BRIDGE_TARGET`
- `OPENCLAW_PYTHON_BIN`
- `OPENCLAW_REMINDER_COMPOSE_COMMAND`

The primary OpenClaw path should read `APPLICATION_NOTIFIER_PAYLOAD_JSON` or `APPLICATION_NOTIFIER_PAYLOAD_FILE` plus `APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS`. The fallback plain-text path only uses `APPLICATION_NOTIFIER_MESSAGE_TEXT` when the structured handoff is unavailable.

### Fine-tuning reminder tone

The base OpenClaw handoff instructions live in [openclaw_bridge.py](/Users/dhnkjc7/Documents/application-notifier/src/application_notifier/openclaw_bridge.py) in `build_handoff_instructions(...)`.

If you want to tune the final message style without editing code, use one or both of:

- `OPENCLAW_REMINDER_STYLE_GUIDE` for short inline guidance
- `OPENCLAW_REMINDER_STYLE_FILE` for longer writing preferences stored in a file

Example:

```env
OPENCLAW_REMINDER_STYLE_GUIDE="Sound like a caring partner. One short greeting, natural wording, no bullet points, no medical advice, and no cheesy enthusiasm."
```

The style guide is appended to the structured instructions that OpenClaw receives. The factual payload stays deterministic; only the phrasing guidance changes.

The bundled wrapper at [deploy/openclaw-reminder-wrapper.sh](/Users/dhnkjc7/Documents/application-notifier/deploy/openclaw-reminder-wrapper.sh) is intentionally tiny:

1. it validates that the structured handoff vars exist
2. it invokes the real OpenClaw compose/send entrypoint you set in `OPENCLAW_REMINDER_COMPOSE_COMMAND`
3. OpenClaw then owns the final phrasing and Telegram delivery

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
sudo systemctl status application-notifier-morning.timer
sudo journalctl -u application-notifier-morning.service -n 100 --no-pager
sudo systemctl start application-notifier-morning.service
```

Timer schedules:

- morning: 08:00
- evening: 20:00
- `Persistent=true` is enabled for both timers

## Manual testing

### Dry-run in the container

```bash
docker exec <openclaw-container> python3 /app/application-notifier/run_reminder.py --slot morning --dry-run
docker exec <openclaw-container> python3 /app/application-notifier/run_reminder.py --slot evening --dry-run
```

### Real run

```bash
docker exec <openclaw-container> python3 /app/application-notifier/run_reminder.py --slot morning
docker exec <openclaw-container> python3 /app/application-notifier/run_reminder.py --slot evening
```

### Bridge contract

The preferred handoff is:

1. notifier builds deterministic facts and grouping
2. notifier passes the structured payload and instructions to OpenClaw
3. OpenClaw composes the final reminder text
4. OpenClaw sends it through the existing Telegram bot/chat loop

The deterministic fallback text is retained only as a last resort if the structured OpenClaw handoff fails and no better OpenClaw-compatible send path is available.

### Container debugging

```bash
docker exec -it <openclaw-container> sh
env | grep -E 'CZM_|OPENCLAW_|APPLICATION_NOTIFIER_'
python3 /app/application-notifier/run_reminder.py --slot morning --print-only
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
5. verify the OpenClaw container has `python3` on PATH, or set `OPENCLAW_PYTHON_BIN`

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
