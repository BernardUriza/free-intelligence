"""FI Backend Sidecar Entry Point.

Single binary CLI dispatcher for FI Monitor's Python backends.
Built with PyInstaller and bundled as a Tauri sidecar.

Usage:
    fi-backend gateway --port 11400
    fi-backend rag --port 11435
"""

from __future__ import annotations

import argparse


def main():
    parser = argparse.ArgumentParser(description="FI Backend Sidecar")
    subparsers = parser.add_subparsers(dest="service", required=True)

    # Gateway subcommand
    gw_parser = subparsers.add_parser("gateway", help="Start HTTP Gateway")
    gw_parser.add_argument("--port", type=int, default=11400)

    # RAG subcommand
    rag_parser = subparsers.add_parser("rag", help="Start RAG Embedding Service")
    rag_parser.add_argument("--port", type=int, default=11435)

    args = parser.parse_args()

    import uvicorn

    if args.service == "gateway":
        from gateway.main import app

        print(f"[fi-backend] Starting Gateway on port {args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)

    elif args.service == "rag":
        from rag_service.main import app

        print(f"[fi-backend] Starting RAG Service on port {args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
