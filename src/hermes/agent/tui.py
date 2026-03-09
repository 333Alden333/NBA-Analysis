"""Terminal UI for Hermes Agent -- interactive REPL with Rich formatting."""

import logging
import os

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

EXIT_COMMANDS = {"exit", "quit", "/q"}

WELCOME_BANNER = """\
[bold cyan]Hermes Agent[/bold cyan] - NBA Analytics Assistant
[dim]Powered by local Ollama LLM with tool-calling agent[/dim]

[bold]Example queries:[/bold]
  - What games are on today?
  - How has LeBron been playing lately?
  - How accurate are the game winner predictions?
  - What's the matchup analysis for Lakers vs Celtics?

[dim]Commands: /help, exit, quit, /q | Ctrl+C or Ctrl+D to exit[/dim]
"""

HELP_TEXT = """\
[bold]Available commands:[/bold]
  [cyan]/help[/cyan]   - Show this help message
  [cyan]exit[/cyan]    - Exit the chat
  [cyan]quit[/cyan]    - Exit the chat
  [cyan]/q[/cyan]      - Exit the chat

[bold]Example queries:[/bold]
  - What games are on today?
  - How has LeBron James been playing recently?
  - Show me prediction accuracy for game spreads
  - What are the predictions for tonight's games?
  - How does Jayson Tatum do against the Lakers?
"""


def _looks_like_markdown(text: str) -> bool:
    """Heuristic check for markdown-like content."""
    indicators = ["# ", "## ", "- ", "* ", "| ", "```", "**", "__"]
    return any(indicator in text for indicator in indicators)


def run_chat(session: Session, model_override: str | None = None) -> None:
    """Launch the interactive Hermes Agent REPL.

    Args:
        session: SQLAlchemy session for database queries.
        model_override: Optional Ollama model name (overrides config).
    """
    from hermes.agent.agent import check_ollama_connection, create_agent
    from hermes.config import settings

    console = Console()

    # Check Ollama connectivity before starting
    if not check_ollama_connection():
        console.print(
            "\n[bold red]Cannot connect to Ollama.[/bold red]\n"
            "\n[bold]Setup instructions:[/bold]\n"
            "  1. Install Ollama: [cyan]curl -fsSL https://ollama.com/install.sh | sh[/cyan]\n"
            "  2. Start the server: [cyan]ollama serve[/cyan]\n"
            f"  3. Pull a model: [cyan]ollama pull {settings.ollama_model}[/cyan]\n"
        )
        return

    # Apply model override if provided
    if model_override:
        settings.ollama_model = model_override

    agent = create_agent(session)

    history_path = os.path.expanduser("~/.hermes_history")
    prompt_session = PromptSession(history=FileHistory(history_path))

    console.print(WELCOME_BANNER)

    try:
        while True:
            try:
                user_input = prompt_session.prompt("You> ")
            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted. Goodbye![/dim]")
                break
            except EOFError:
                console.print("\n[dim]Goodbye![/dim]")
                break

            stripped = user_input.strip()

            if not stripped:
                continue

            if stripped.lower() in EXIT_COMMANDS:
                console.print("[dim]Goodbye![/dim]")
                break

            if stripped.lower() == "/help":
                console.print(HELP_TEXT)
                continue

            try:
                response = agent.run(stripped, reset=False)
                response_text = str(response)
            except Exception as e:
                logger.error("Agent error: %s", e, exc_info=True)
                console.print(
                    f"[bold red]Error:[/bold red] {e}\n"
                    "[dim]The agent encountered an error. Try rephrasing your question.[/dim]"
                )
                continue

            console.print()
            if _looks_like_markdown(response_text):
                console.print("[bold cyan]Hermes>[/bold cyan]")
                console.print(Markdown(response_text))
            else:
                console.print(f"[bold cyan]Hermes>[/bold cyan] {response_text}")
            console.print()

    except Exception as e:
        logger.error("TUI loop error: %s", e, exc_info=True)
        console.print(f"[bold red]Fatal error:[/bold red] {e}")
