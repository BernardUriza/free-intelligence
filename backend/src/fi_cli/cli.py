from __future__ import annotations

from typing import Annotated

import typer
from pathlib import Path

from .domains import auth, coder, data, deploy, dev, infra, ops

app = typer.Typer(
    name="fi-cli",
    help="AURITY unified operational CLI.",
    no_args_is_help=True,
)


BasePathOpt = Annotated[
    Path | None,
    typer.Option(
        "--base-path",
        help="Absolute path to repo root or backend/ directory.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
]


@app.callback()
def _root_callback(
    base_path: BasePathOpt = None,
) -> None:
    # Reserved for future global context wiring.
    _ = base_path


app.add_typer(dev.app, name="dev")
app.add_typer(ops.app, name="ops")
app.add_typer(deploy.app, name="deploy")
app.add_typer(auth.app, name="auth")
app.add_typer(data.app, name="data")
app.add_typer(infra.app, name="infra")
app.add_typer(coder.app, name="coder")


if __name__ == "__main__":
    app()
