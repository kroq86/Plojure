#!/usr/bin/env python3

import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until the vector-db MCP server reports ready.")
    parser.add_argument("--url", default="http://127.0.0.1:8765/ready", help="Readiness endpoint URL")
    parser.add_argument("--timeout", type=float, default=120.0, help="Maximum seconds to wait")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    args = parser.parse_args()

    deadline = time.monotonic() + args.timeout
    last_error = "unknown error"

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(args.url, timeout=3) as response:
                payload = json.load(response)
            if payload.get("ready"):
                print(json.dumps(payload))
                return 0
            last_error = json.dumps(payload)
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ValueError, OSError) as exc:
            last_error = str(exc)
        time.sleep(args.interval)

    print(f"MCP server did not become ready before timeout: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
