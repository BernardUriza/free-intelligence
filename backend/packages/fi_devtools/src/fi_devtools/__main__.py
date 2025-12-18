from __future__ import annotations


def main() -> None:
    # Import inside the function to keep import side-effects minimal.
    from .cli import app

    app()


if __name__ == "__main__":
    main()
