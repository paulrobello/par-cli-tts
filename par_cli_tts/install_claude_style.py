#!/usr/bin/env python
"""
Install the TTS Summary output style for Claude Code.

This is a separate CLI entry point to avoid conflicts with the main
par-tts command's argument parsing.
"""

import json
import re
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.prompt import Prompt

from par_cli_tts.console import console

app = typer.Typer(
    help="Install TTS Summary output style for Claude Code",
    no_args_is_help=True,
)


@app.command()
def install(
    user_name: Annotated[
        str | None,
        typer.Option(
            "-n",
            "--name",
            help="Your name for personalized audio summaries",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "-f",
            "--force",
            help="Overwrite existing output style if it exists",
        ),
    ] = False,
) -> None:
    """
    Install the TTS Summary output style for Claude Code.

    This command installs the TTS Summary output style to your Claude Code
    configuration and grants permission for Claude to run par-tts commands.
    After installation, activate it in Claude Code with: /output-style tts-summary
    """
    # Define paths using cross-platform home directory
    claude_dir = Path.home() / ".claude"
    output_styles_dir = claude_dir / "output-styles"
    settings_file = claude_dir / "settings.json"
    output_style_file = output_styles_dir / "tts-summary.md"

    # Get the bundled output style from the package
    # Try multiple locations for cross-platform compatibility
    possible_paths = [
        # Installed package location (relative to this file)
        Path(__file__).parent.parent / ".claude" / "output-styles" / "tts-summary.md",
        # Current working directory (for development)
        Path.cwd() / ".claude" / "output-styles" / "tts-summary.md",
    ]

    bundled_style = None
    for path in possible_paths:
        if path.exists():
            bundled_style = path
            break

    if not bundled_style:
        console.print("[red]Error: Could not find bundled output style file.[/red]")
        console.print("[dim]Searched locations:[/dim]")
        for path in possible_paths:
            console.print(f"  [dim]- {path}[/dim]")
        raise typer.Exit(1)

    # Prompt for user name if not provided
    if not user_name:
        user_name = Prompt.ask(
            "[cyan]Enter your name for personalized audio summaries[/cyan]",
            default="User",
        )

    # Create directories if they don't exist
    try:
        output_styles_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[dim]Ensured directory exists: {output_styles_dir}[/dim]")
    except PermissionError:
        console.print(f"[red]Error: Permission denied creating directory: {output_styles_dir}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error creating directory: {e}[/red]")
        raise typer.Exit(1)

    # Check if output style already exists
    if output_style_file.exists() and not force:
        console.print("[yellow]Output style already exists at:[/yellow]", output_style_file)
        console.print("[dim]Use --force to overwrite[/dim]")
    else:
        # Copy and customize the output style
        console.print("[cyan]Installing TTS Summary output style...[/cyan]")

        try:
            content = bundled_style.read_text(encoding="utf-8")

            # Customize the user name in the content
            content = re.sub(
                r"\*\*USER_NAME\*\*:\s*\w+",
                f"**USER_NAME**: {user_name}",
                content,
            )
            content = re.sub(
                r"## Audio Summary for \w+",
                f"## Audio Summary for {user_name}",
                content,
            )
            content = re.sub(
                r"Address \w+ directly",
                f"Address {user_name} directly",
                content,
            )
            content = re.sub(
                r"Paul,",
                f"{user_name},",
                content,
            )
            content = re.sub(
                r'"Paul,',
                f'"{user_name},',
                content,
            )
            content = re.sub(
                r"\[Bash tool call: par-tts \"[^\"]*Paul",
                f'[Bash tool call: par-tts "{user_name}',
                content,
            )

            output_style_file.write_text(content, encoding="utf-8")
            console.print(f"[green]✓ Installed output style to: {output_style_file}[/green]")
        except PermissionError:
            console.print(f"[red]Error: Permission denied writing to: {output_style_file}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Failed to copy output style: {e}[/red]")
            raise typer.Exit(1)

    # Update settings.json with permission
    console.print("[cyan]Updating Claude Code permissions...[/cyan]")

    settings: dict[str, Any] = {}
    if settings_file.exists():
        try:
            file_content = settings_file.read_text(encoding="utf-8")
            if file_content.strip():
                settings = json.loads(file_content)
                console.print("[dim]Loaded existing settings.json[/dim]")
            else:
                console.print("[dim]settings.json is empty, creating new configuration[/dim]")
                settings = {}
        except json.JSONDecodeError as e:
            console.print(f"[yellow]Warning: Could not parse existing settings.json: {e}[/yellow]")
            console.print("[yellow]Creating backup and new configuration[/yellow]")
            # Create backup
            backup_file = settings_file.with_suffix(".json.backup")
            try:
                settings_file.rename(backup_file)
                console.print(f"[dim]Backup created: {backup_file}[/dim]")
            except Exception:
                pass
            settings = {}
        except PermissionError:
            console.print(f"[red]Error: Permission denied reading: {settings_file}[/red]")
            raise typer.Exit(1)

    # Ensure permissions structure exists (handle missing or null values)
    if "permissions" not in settings or settings["permissions"] is None:
        settings["permissions"] = {}
    if "allow" not in settings["permissions"] or settings["permissions"]["allow"] is None:
        settings["permissions"]["allow"] = []

    # Ensure allow is a list (handle edge cases)
    if not isinstance(settings["permissions"]["allow"], list):
        console.print("[yellow]Warning: permissions.allow is not a list, resetting[/yellow]")
        settings["permissions"]["allow"] = []

    # Add par-tts permission if not already present (avoid duplicates)
    par_tts_permission = "Bash(par-tts:*)"
    if par_tts_permission not in settings["permissions"]["allow"]:
        settings["permissions"]["allow"].append(par_tts_permission)
        console.print(f"[green]✓ Added permission: {par_tts_permission}[/green]")
    else:
        console.print(f"[dim]Permission already exists: {par_tts_permission}[/dim]")

    # Write updated settings
    try:
        settings_file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        console.print(f"[green]✓ Updated settings: {settings_file}[/green]")
    except PermissionError:
        console.print(f"[red]Error: Permission denied writing to: {settings_file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to update settings.json: {e}[/red]")
        raise typer.Exit(1)

    # Success message
    console.print()
    console.print("[bold green]Installation complete![/bold green]")
    console.print()
    console.print("[cyan]To activate the output style in Claude Code, run:[/cyan]")
    console.print("  [bold]/output-style tts-summary[/bold]")
    console.print()
    console.print(f"[dim]Your name is set to: {user_name}[/dim]")
    console.print(f"[dim]To change your name, edit: {output_style_file}[/dim]")


if __name__ == "__main__":
    app()
