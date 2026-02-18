#!/usr/bin/env python3
"""
FI Edge Server - Lightweight Observability Backend

Intercepta y loguea todas las llamadas a Ollama localmente.

Modos:
- Cloud+Edge: Corre en el NUC, intercepta calls del tunnel
- OnlyEdge: Parte de la app "FI" standalone

Uso:
    python -m fi_edge.server                    # Puerto default 9200
    python -m fi_edge.server --port 9200        # Puerto custom
    FI_EDGE_PORT=9200 python -m fi_edge.server  # Via env var

Endpoints:
    GET  /health              - Health check
    GET  /status              - Ollama + system status
    GET  /stats               - Estadísticas agregadas
    GET  /calls               - Llamadas recientes
    GET  /calls/{id}          - Detalle de una llamada
    POST /proxy/chat          - Proxy a Ollama con logging
"""

import argparse
import hashlib
import json
import logging
import platform
import sqlite3
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import os
from pathlib import Path

# Config
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DB_PATH = Path(os.getenv("FI_EDGE_DB", Path.home() / ".fi" / "edge_observability.db"))
DEFAULT_PORT = int(os.getenv("FI_EDGE_PORT", "9200"))

# Housekeeper config
MAX_RECORDS = int(os.getenv("FI_EDGE_MAX_RECORDS", "1000"))  # Keep last 1000 calls
MAX_AGE_HOURS = int(os.getenv("FI_EDGE_MAX_AGE_HOURS", "24"))  # Keep last 24 hours
HOUSEKEEP_INTERVAL = 300  # Run every 5 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fi-edge")


# =============================================================================
# DATABASE
# =============================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_calls (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success',
    error_message TEXT,
    prompt_preview TEXT,
    response_preview TEXT,
    prompt_hash TEXT,
    response_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON llm_calls(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_model ON llm_calls(model);
CREATE INDEX IF NOT EXISTS idx_status ON llm_calls(status);
"""


def init_db():
    """Initialize SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info(f"Database initialized: {DB_PATH}")


@contextmanager
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def generate_id():
    """Generate a simple time-based ID."""
    import random

    return f"{int(time.time() * 1000)}-{random.randint(1000, 9999)}"


# =============================================================================
# HOUSEKEEPER
# =============================================================================


def run_housekeeping() -> dict:
    """Clean old records from the database."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)).isoformat()

    with get_db() as conn:
        # Count before
        count_before = conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0]

        # Delete old records
        conn.execute("DELETE FROM llm_calls WHERE timestamp < ?", (cutoff,))

        # Keep only MAX_RECORDS (delete oldest if over limit)
        conn.execute(
            """
            DELETE FROM llm_calls WHERE id NOT IN (
                SELECT id FROM llm_calls ORDER BY timestamp DESC LIMIT ?
            )
        """,
            (MAX_RECORDS,),
        )

        conn.commit()

        # Count after
        count_after = conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0]

    deleted = count_before - count_after
    if deleted > 0:
        logger.info(f"Housekeeping: deleted {deleted} old records, {count_after} remaining")

    return {"deleted": deleted, "remaining": count_after}


def start_housekeeper():
    """Start background housekeeper thread."""
    import threading

    def housekeep_loop():
        while True:
            try:
                time.sleep(HOUSEKEEP_INTERVAL)
                run_housekeeping()
            except Exception as e:
                logger.warning(f"Housekeeping error: {e}")

    thread = threading.Thread(target=housekeep_loop, daemon=True)
    thread.start()
    logger.info(f"Housekeeper started (max {MAX_RECORDS} records, {MAX_AGE_HOURS}h retention)")


# =============================================================================
# OLLAMA CLIENT
# =============================================================================


def ensure_ollama_running() -> bool:
    """Ensure Ollama is running, start it if not."""
    # Check if already running
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                logger.info("Ollama already running")
                return True
    except Exception:
        pass

    # Try to start Ollama
    logger.info("Ollama not running, attempting to start...")
    try:
        import shutil
        import subprocess

        # Find ollama executable
        ollama_path = shutil.which("ollama")
        if not ollama_path:
            # Windows common paths
            for path in [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
                r"C:\Program Files\Ollama\ollama.exe",
                "/usr/local/bin/ollama",
                "/opt/homebrew/bin/ollama",
            ]:
                if os.path.exists(path):
                    ollama_path = path
                    break

        if not ollama_path:
            logger.warning("Ollama executable not found")
            return False

        # Set CORS environment
        env = os.environ.copy()
        env["OLLAMA_ORIGINS"] = "*"
        env["OLLAMA_HOST"] = "0.0.0.0:11434"

        # Start ollama serve in background
        if platform.system() == "Windows":
            subprocess.Popen(
                [ollama_path, "serve"],
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [ollama_path, "serve"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        # Wait for Ollama to start
        for _ in range(10):
            time.sleep(1)
            try:
                req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        logger.info("Ollama started successfully")
                        return True
            except Exception:
                pass

        logger.warning("Ollama started but not responding")
        return False

    except Exception as e:
        logger.warning(f"Failed to start Ollama: {e}")
        return False


def check_ollama() -> dict:
    """Check Ollama status."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            return {"status": "running", "models": models}
    except Exception as e:
        return {"status": "stopped", "error": str(e), "models": []}


def get_loaded_model() -> dict:
    """Get currently loaded model info."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/ps", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("models"):
                m = data["models"][0]
                size_gb = round(m.get("size", 0) / (1024**3), 2)
                return {"name": m.get("name", "unknown"), "size_gb": size_gb, "loaded": True}
    except Exception:
        pass
    return {"name": None, "size_gb": 0, "loaded": False}


def call_ollama_chat(model: str, messages: list, **kwargs) -> tuple[dict, int]:
    """Call Ollama chat API and return response + latency."""
    payload = {"model": model, "messages": messages, "stream": False, **kwargs}

    start = time.time()
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            latency_ms = int((time.time() - start) * 1000)
            return result, latency_ms
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"error": str(e)}, latency_ms


# =============================================================================
# LOGGING
# =============================================================================


def log_call(
    model: str,
    latency_ms: int,
    prompt_preview: str = "",
    response_preview: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    status: str = "success",
    error_message: str | None = None,
) -> str:
    """Log an LLM call to the database."""
    call_id = generate_id()
    timestamp = datetime.now(timezone.utc).isoformat()

    prompt_hash = hashlib.sha256(prompt_preview.encode()).hexdigest()[:16] if prompt_preview else ""
    response_hash = (
        hashlib.sha256(response_preview.encode()).hexdigest()[:16] if response_preview else ""
    )

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO llm_calls (
                id, timestamp, model, prompt_tokens, completion_tokens, total_tokens,
                latency_ms, status, error_message, prompt_preview, response_preview,
                prompt_hash, response_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                timestamp,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                latency_ms,
                status,
                error_message,
                prompt_preview[:500],
                response_preview[:500],
                prompt_hash,
                response_hash,
            ),
        )
        conn.commit()

    logger.info(f"Logged call {call_id}: {model} ({latency_ms}ms) [{status}]")
    return call_id


def get_stats(hours: int = 24) -> dict:
    """Get aggregated statistics."""
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
                SUM(total_tokens) as tokens,
                AVG(latency_ms) as avg_latency,
                MIN(latency_ms) as min_latency,
                MAX(latency_ms) as max_latency
            FROM llm_calls
            WHERE timestamp >= ?
            """,
            (since,),
        ).fetchone()

        models = conn.execute(
            """
            SELECT model, COUNT(*) as count, SUM(total_tokens) as tokens, AVG(latency_ms) as avg_latency
            FROM llm_calls
            WHERE timestamp >= ?
            GROUP BY model
            ORDER BY count DESC
            """,
            (since,),
        ).fetchall()

        return {
            "period_hours": hours,
            "total_calls": row["total"] or 0,
            "success_calls": row["success"] or 0,
            "error_calls": row["errors"] or 0,
            "total_tokens": row["tokens"] or 0,
            "avg_latency_ms": round(row["avg_latency"] or 0, 1),
            "min_latency_ms": row["min_latency"] or 0,
            "max_latency_ms": row["max_latency"] or 0,
            "by_model": [
                {
                    "model": m["model"],
                    "count": m["count"],
                    "tokens": m["tokens"] or 0,
                    "avg_latency_ms": round(m["avg_latency"] or 0, 1),
                }
                for m in models
            ],
        }


def get_recent_calls(limit: int = 10) -> list:
    """Get recent calls."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM llm_calls ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_call(call_id: str) -> dict | None:
    """Get a specific call."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM llm_calls WHERE id = ?", (call_id,)).fetchone()
        return dict(row) if row else None


# =============================================================================
# SYSTEM INFO
# =============================================================================


def get_system_info() -> dict:
    """Get system information."""
    try:
        import psutil

        memory = psutil.virtual_memory()
        return {
            "platform": platform.system(),
            "hostname": platform.node(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_total_gb": round(memory.total / (1024**3), 1),
            "memory_used_gb": round(memory.used / (1024**3), 1),
            "memory_percent": memory.percent,
        }
    except ImportError:
        return {
            "platform": platform.system(),
            "hostname": platform.node(),
            "note": "Install psutil for detailed metrics",
        }


# =============================================================================
# HTTP SERVER
# =============================================================================


class EdgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Edge Server."""

    def log_message(self, format, *args):  # noqa: A002
        """Suppress default logging."""
        pass

    def send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        path = self.path.split("?")[0]

        if path == "/health":
            self.send_json({"status": "ok", "service": "fi-edge-server"})

        elif path == "/status":
            ollama = check_ollama()
            model = get_loaded_model()
            system = get_system_info()
            self.send_json(
                {
                    "ollama": ollama,
                    "model": model,
                    "system": system,
                    "ollama_url": OLLAMA_URL,
                }
            )

        elif path == "/stats":
            hours = 24
            if "?" in self.path:
                params = dict(p.split("=") for p in self.path.split("?")[1].split("&") if "=" in p)
                hours = int(params.get("hours", 24))
            self.send_json(get_stats(hours))

        elif path == "/calls":
            limit = 10
            if "?" in self.path:
                params = dict(p.split("=") for p in self.path.split("?")[1].split("&") if "=" in p)
                limit = int(params.get("limit", 10))
            self.send_json({"calls": get_recent_calls(limit)})

        elif path.startswith("/calls/"):
            call_id = path.split("/")[-1]
            call = get_call(call_id)
            if call:
                self.send_json(call)
            else:
                self.send_json({"error": "Call not found"}, 404)

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        path = self.path.split("?")[0]

        if path == "/proxy/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()

            try:
                req = json.loads(body)
                model = req.get("model", "qwen3:1.7b")
                messages = req.get("messages", [])
                think = req.get("think", False)

                prompt_preview = ""
                if messages:
                    last_msg = messages[-1]
                    prompt_preview = last_msg.get("content", "")[:500]

                result, latency_ms = call_ollama_chat(model, messages, think=think)

                response_preview = ""
                total_tokens = 0
                status = "success"
                error_message = None

                if "error" in result:
                    status = "error"
                    error_message = result["error"]
                else:
                    if "message" in result and "content" in result["message"]:
                        response_preview = result["message"]["content"][:500]
                    if "eval_count" in result:
                        total_tokens = result.get("prompt_eval_count", 0) + result.get(
                            "eval_count", 0
                        )

                call_id = log_call(
                    model=model,
                    latency_ms=latency_ms,
                    prompt_preview=prompt_preview,
                    response_preview=response_preview,
                    total_tokens=total_tokens,
                    status=status,
                    error_message=error_message,
                )

                result["_call_id"] = call_id
                result["_latency_ms"] = latency_ms
                self.send_json(result)

            except Exception as e:
                logger.error(f"Proxy error: {e}")
                self.send_json({"error": str(e)}, 500)

        else:
            self.send_json({"error": "Not found"}, 404)


def run_server(port: int = DEFAULT_PORT):
    """Run the HTTP server."""
    init_db()
    ensure_ollama_running()
    start_housekeeper()

    server = HTTPServer(("0.0.0.0", port), EdgeHandler)
    logger.info("")
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║  FI Edge Server v0.1.0                                    ║")
    logger.info("╠═══════════════════════════════════════════════════════════╣")
    logger.info(f"║  Port:     {port:<47} ║")
    logger.info(f"║  Ollama:   {OLLAMA_URL:<47} ║")
    logger.info(f"║  Database: {DB_PATH!s:<47} ║")
    logger.info("╠═══════════════════════════════════════════════════════════╣")
    logger.info("║  Endpoints:                                               ║")
    logger.info("║    GET  /health     - Health check                        ║")
    logger.info("║    GET  /status     - Ollama + system status              ║")
    logger.info("║    GET  /stats      - Call statistics                     ║")
    logger.info("║    GET  /calls      - Recent calls                        ║")
    logger.info("║    POST /proxy/chat - Proxy to Ollama with logging        ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝")
    logger.info("")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="FI Edge Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to run on")
    args = parser.parse_args()
    run_server(args.port)


if __name__ == "__main__":
    main()
