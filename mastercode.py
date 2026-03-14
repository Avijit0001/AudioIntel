import os
import time
import json
import subprocess
import signal
import sys
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
TEST = True                        # ← Change to False for production mode

GET_URLS_FOLDER     = "get_urls"      # Folder containing URL-fetching scripts
GET_PRODUCTS_FOLDER = "get_products"  # Folder containing product-scraping scripts

# JSON files to merge (must exist after get_products finishes)
JSON_FILES_TO_MERGE = [
    "pickaboo_products.json",
    "startech_products.json",
    "techland_products.json",
]
MERGED_OUTPUT_FILE  = "products.json"

# Embedder script to run after merging
EMBEDDER_SCRIPT     = os.path.join("embeddding", "embedder.py")   # note: folder name as given

# Derived timing constants
URL_TIMEOUT_SECONDS = 60    if TEST else None   # 1 min limit in TEST, unlimited otherwise
SCHEDULE_INTERVAL   = 240   if TEST else 86400  # 4 min in TEST, 24 hrs otherwise

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}]  {msg}", flush=True)


def get_python_files(folder: str) -> list[str]:
    """Return sorted list of .py files inside *folder*."""
    if not os.path.isdir(folder):
        log(f"WARNING: folder '{folder}' not found – skipping.")
        return []
    files = sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(".py")
    )
    return files


def run_script(path: str) -> subprocess.Popen:
    """Start a script in a subprocess and return the Popen handle."""
    log(f"  ▶ Starting: {path}")
    return subprocess.Popen(
        [sys.executable, path],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


# ─────────────────────────────────────────────
#  PHASE 1 – run get_urls (with optional timeout)
# ─────────────────────────────────────────────

def run_get_urls():
    scripts = get_python_files(GET_URLS_FOLDER)
    if not scripts:
        log("No scripts found in get_urls – skipping phase.")
        return

    log(f"━━━ Phase 1 · get_urls  (timeout={'%ds' % URL_TIMEOUT_SECONDS if URL_TIMEOUT_SECONDS else 'none'}) ━━━")

    processes: list[subprocess.Popen] = []
    for script in scripts:
        proc = run_script(script)
        processes.append(proc)

    if URL_TIMEOUT_SECONDS is None:
        # No time limit – wait for all to finish naturally
        for proc in processes:
            proc.wait()
    else:
        # Wait up to URL_TIMEOUT_SECONDS, then kill any still-running process
        deadline = time.time() + URL_TIMEOUT_SECONDS
        for proc in processes:
            remaining = deadline - time.time()
            if remaining <= 0:
                log(f"  ⏱  Timeout reached – terminating remaining get_urls processes.")
                proc.terminate()
                continue
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                log(f"  ⏱  Timeout reached – terminating process pid={proc.pid}")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    log("━━━ Phase 1 complete ━━━")


# ─────────────────────────────────────────────
#  PHASE 2 – run get_products (no time limit)
# ─────────────────────────────────────────────

def run_get_products():
    scripts = get_python_files(GET_PRODUCTS_FOLDER)
    if not scripts:
        log("No scripts found in get_products – skipping phase.")
        return

    log("━━━ Phase 2 · get_products  (no time limit) ━━━")

    for script in scripts:
        proc = run_script(script)
        proc.wait()   # Run sequentially; swap for parallel if preferred

    log("━━━ Phase 2 complete ━━━")


# ─────────────────────────────────────────────
#  PHASE 3 – merge JSON files → products.json
# ─────────────────────────────────────────────

def merge_json_files():
    log("━━━ Phase 3 · Merging JSON files ━━━")

    merged: list = []
    missing: list[str] = []

    for filename in JSON_FILES_TO_MERGE:
        if not os.path.isfile(filename):
            log(f"  ⚠  File not found, skipping: {filename}")
            missing.append(filename)
            continue

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                merged.extend(data)
                log(f"  ✔  {filename}  →  {len(data)} records loaded")
            elif isinstance(data, dict):
                # If the file wraps products in a key, flatten it; otherwise wrap in list
                # Try common wrapper keys first, then fall back to the whole dict
                found = False
                for key in ("products", "data", "items", "results"):
                    if key in data and isinstance(data[key], list):
                        merged.extend(data[key])
                        log(f"  ✔  {filename}  →  {len(data[key])} records loaded (key='{key}')")
                        found = True
                        break
                if not found:
                    merged.append(data)
                    log(f"  ✔  {filename}  →  1 record loaded (single dict)")
            else:
                log(f"  ⚠  Unexpected JSON type in {filename} – skipping.")

        except json.JSONDecodeError as e:
            log(f"  ✖  JSON decode error in {filename}: {e}")
        except Exception as e:
            log(f"  ✖  Error reading {filename}: {e}")

    if missing:
        log(f"  ℹ  {len(missing)} file(s) were missing and skipped.")

    try:
        with open(MERGED_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        log(f"  ✔  Merged {len(merged)} total records → {MERGED_OUTPUT_FILE}")
    except Exception as e:
        log(f"  ✖  Failed to write {MERGED_OUTPUT_FILE}: {e}")

    log("━━━ Phase 3 complete ━━━")


# ─────────────────────────────────────────────
#  PHASE 4 – run embedding/embedder.py
# ─────────────────────────────────────────────

def run_embedder():
    log("━━━ Phase 4 · Running embedder ━━━")

    if not os.path.isfile(EMBEDDER_SCRIPT):
        log(f"  ⚠  Embedder script not found at '{EMBEDDER_SCRIPT}' – skipping.")
        log("━━━ Phase 4 skipped ━━━")
        return

    log(f"  ▶ Starting: {EMBEDDER_SCRIPT}")
    proc = subprocess.Popen(
        [sys.executable, EMBEDDER_SCRIPT],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    proc.wait()

    if proc.returncode == 0:
        log(f"  ✔  Embedder finished successfully (exit code 0)")
    else:
        log(f"  ✖  Embedder exited with code {proc.returncode}")

    log("━━━ Phase 4 complete ━━━")


# ─────────────────────────────────────────────
#  ONE FULL CYCLE
# ─────────────────────────────────────────────

def run_cycle(cycle_number: int):
    log(f"╔══════════════════════════════════════╗")
    log(f"  Cycle #{cycle_number}  |  TEST={TEST}")
    log(f"╚══════════════════════════════════════╝")

    run_get_urls()
    run_get_products()
    merge_json_files()
    run_embedder()

    log(f"✔  Cycle #{cycle_number} finished.\n")


# ─────────────────────────────────────────────
#  SCHEDULER
# ─────────────────────────────────────────────

def scheduler():
    cycle = 1
    interval_label = "4 minutes" if TEST else "24 hours"

    log(f"Scheduler started  |  TEST={TEST}  |  interval={interval_label}")

    while True:
        run_cycle(cycle)

        next_run = datetime.now() + timedelta(seconds=SCHEDULE_INTERVAL)
        log(f"Next cycle scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S')}  ({interval_label} from now)\n")

        # Sleep in small ticks so Ctrl-C is responsive
        for _ in range(SCHEDULE_INTERVAL):
            time.sleep(1)

        cycle += 1


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def handle_signal(sig, frame):
    log("Interrupt received – shutting down scheduler.")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT,  handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    scheduler()