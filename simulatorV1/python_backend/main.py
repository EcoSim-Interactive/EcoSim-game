"""Backward compatible entry point forwarding to app.main."""
from app.main import run_cli


if __name__ == "__main__":
    run_cli()
