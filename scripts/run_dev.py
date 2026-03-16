"""Development launcher — starts FastAPI and Dash concurrently."""

import signal
import subprocess
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path when run directly
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402

settings = get_settings()


def main() -> None:
    api_cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", settings.API_HOST,
        "--port", str(settings.API_PORT),
        "--reload",
    ]

    dash_cmd = [
        sys.executable, "-m", "app.dashboard.app",
    ]

    print(f"[run_dev] Starting FastAPI on http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"[run_dev] Starting Dash on  http://{settings.DASH_HOST}:{settings.DASH_PORT}")

    procs = [
        subprocess.Popen(api_cmd, cwd=ROOT),
        subprocess.Popen(dash_cmd, cwd=ROOT),
    ]

    def _shutdown(sig: int, _frame: object) -> None:
        print("\n[run_dev] Shutting down…")
        for p in procs:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    print(f"[run_dev] Process {p.pid} exited with code {p.returncode}")
                    _shutdown(0, None)
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown(0, None)


if __name__ == "__main__":
    main()
