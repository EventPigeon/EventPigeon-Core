import json
import os
import signal
import sys
from typing import Dict, List, Tuple

import redis


def get_client() -> redis.Redis:
    url = os.getenv("REDIS_URL")
    if url:
        return redis.Redis.from_url(url, decode_responses=True)
    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    return redis.Redis(host=host, port=port, db=db, decode_responses=True)


def pretty_print_alert(alert: Dict) -> None:
    print(json.dumps(alert, indent=2, sort_keys=True))


def main() -> None:
    start_from_beginning = os.getenv("FROM_START", "false").lower() in {"1", "true", "yes"}
    start_id = "0-0" if start_from_beginning else "$"

    client = get_client()
    stream = os.getenv("ALERTS_STREAM", "alerts")

    print(f"[subscriber] Listening on stream '{stream}' (start_id={start_id})...")
    print("Press Ctrl+C to exit.")

    # Graceful shutdown support
    should_stop = False

    def _handle_sigint(signum, frame):
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    while not should_stop:
        # XREAD blocks until a new message arrives
        messages: List[Tuple[str, List[Tuple[str, Dict[str, str]]]]] = client.xread(
            {stream: start_id}, count=1, block=0
        )
        if not messages:
            continue
        # messages is a list of (stream_name, [(id, {field: value, ...}), ...])
        for _stream_name, entries in messages:
            for entry_id, fields in entries:
                raw = fields.get("alert")
                if raw:
                    try:
                        alert = json.loads(raw)
                        pretty_print_alert(alert)
                    except json.JSONDecodeError:
                        print(f"[subscriber] Received malformed JSON for entry {entry_id}")
                # Update start_id to the last seen ID to continue
                start_id = entry_id

    print("[subscriber] Exiting.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[subscriber] Interrupted.")
        sys.exit(0)

