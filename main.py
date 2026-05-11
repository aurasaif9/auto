"""
main.py — Background worker + HTTP keep-alive server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Runs wingo_bot.run() in an infinite loop (every 60 seconds)
✅ HTTP server keeps Render free plan from sleeping
✅ Catches ALL errors so process never exits early
✅ Auto-retry on temporary DNS / network failures
"""

import os
import time
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import wingo_bot


# ====== HTTP SERVER (keep-alive for Render) ======
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - AURA X Wingo bot running")

    def log_message(self, format, *args):
        return  # silence default access logs


def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
        print(f"[http] Listening on 0.0.0.0:{port}", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[http] error: {e}", flush=True)


# ====== BACKGROUND WORKER ======
# Render free plan = 1-minute Wingo period, so we tick every 60s.
TICK_SECONDS = 60


def run_worker():
    print("[worker] AURA X Wingo bot worker started", flush=True)
    consecutive_errors = 0

    while True:
        start = time.time()
        try:
            wingo_bot.run()
            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            print(f"[worker] tick error #{consecutive_errors}: {e}", flush=True)
            traceback.print_exc()
            # Back off slightly on repeated failures, but never exit
            if consecutive_errors >= 5:
                print("[worker] many failures — sleeping 30s extra", flush=True)
                time.sleep(30)

        elapsed = time.time() - start
        sleep_for = max(5, TICK_SECONDS - elapsed)
        time.sleep(sleep_for)


# ====== ENTRYPOINT ======
def main():
    # HTTP server in background thread (daemon = dies with main process)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Worker loop in main thread — keeps the process alive forever
    while True:
        try:
            run_worker()
        except Exception as e:
            print(f"[main] worker crashed: {e} — restarting in 10s", flush=True)
            traceback.print_exc()
            time.sleep(10)


if __name__ == "__main__":
    main()
