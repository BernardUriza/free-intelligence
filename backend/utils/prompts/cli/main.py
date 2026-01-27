"""Simplified prompt CLI tool for retrieving and customizing prompts.

This module provides a command-line interface to access the prompt library,
allowing users to retrieve pre-defined prompts with custom parameters.
"""

from __future__ import annotations

import json

import sys
import typer
from backend.utils.prompts.prompt_provider import (
    get_available_prompts,
    get_prompt,
    get_prompt_metadata,
)
from pathlib import Path

app = typer.Typer(help="FI Prompts - Prompt Library CLI")


@app.command()
def list() -> None:
    """List all available prompt types."""
    prompts = get_available_prompts()
    typer.echo("Available prompt types:")
    for prompt in sorted(prompts):
        typer.echo(f"  - {prompt}")


@app.command()
def get(
    prompt_type: str = typer.Argument(..., help="Type of prompt to retrieve"),
    params_file: Path = typer.Option(
        None, "--params", "-f", help="JSON file with parameters for the prompt"
    ),
    output_file: Path = typer.Option(None, "--output", "-o", help="Output file to save the prompt"),
    params: str = typer.Option(
        "", "--param", "-p", help="Parameter in format key=value (can be used multiple times)"
    ),
) -> None:
    """Retrieve a prompt with specified parameters."""
    # Parse parameters from command line
    parsed_params = {}

    # From params option (multiple -p options allowed)
    if params:
        for param in params.split(","):
            if "=" in param:
                key, value = param.split("=", 1)
                parsed_params[key] = value

    # From JSON file
    if params_file:
        if not params_file.exists():
            typer.echo(f"Error: Parameter file not found: {params_file}", err=True)
            sys.exit(1)

        try:
            with open(params_file) as f:
                file_params = json.load(f)
            parsed_params.update(file_params)
        except json.JSONDecodeError as e:
            typer.echo(f"Error: Invalid JSON in parameter file: {e}", err=True)
            sys.exit(1)

    # Retrieve the prompt
    try:
        prompt = get_prompt(prompt_type, **parsed_params)

        if output_file:
            # Write to output file
            output_file.write_text(prompt, encoding="utf-8")
            typer.echo(f"Prompt saved to {output_file}")
        else:
            # Print to stdout
            print(prompt)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)


@app.command()
def info(
    prompt_type: str = typer.Argument(..., help="Type of prompt to get info for"),
) -> None:
    """Get information about a specific prompt."""
    try:
        metadata = get_prompt_metadata(prompt_type)
        print(json.dumps(metadata, indent=2))
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)


@app.command()
def template(
    prompt_type: str = typer.Argument(..., help="Type of prompt to get template for"),
) -> None:
    """Get the raw template for a specific prompt."""
    provider = __import__(
        "backend.src.fi_prompts.prompt_provider", fromlist=["PromptProvider"]
    ).get_prompt_provider()
    templates = provider._templates

    if prompt_type not in templates:
        available = list(templates.keys())
        typer.echo(f"Error: Unknown prompt type: {prompt_type}. Available: {available}", err=True)
        sys.exit(1)

    print(templates[prompt_type])


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
