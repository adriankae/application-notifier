#!/usr/bin/env sh
set -eu

: "${APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS:?missing APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS}"
: "${APPLICATION_NOTIFIER_PAYLOAD_JSON:?missing APPLICATION_NOTIFIER_PAYLOAD_JSON}"
: "${OPENCLAW_BRIDGE_TARGET:?missing OPENCLAW_BRIDGE_TARGET}"
: "${OPENCLAW_REMINDER_COMPOSE_COMMAND:?set OPENCLAW_REMINDER_COMPOSE_COMMAND to the OpenClaw compose/send entrypoint}"

# The notifier hands OpenClaw facts plus instructions. This wrapper's job is
# only to invoke the real OpenClaw-side compose/send command.
exec sh -lc "$OPENCLAW_REMINDER_COMPOSE_COMMAND"
