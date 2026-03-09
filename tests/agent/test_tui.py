"""Tests for the Hermes Agent TUI (terminal UI)."""

from unittest.mock import MagicMock, patch

import pytest


def test_run_chat_importable():
    """run_chat is importable from the tui module."""
    from hermes.agent.tui import run_chat
    assert callable(run_chat)


def test_exit_commands_defined():
    """EXIT_COMMANDS contains the expected exit keywords."""
    from hermes.agent.tui import EXIT_COMMANDS
    assert "exit" in EXIT_COMMANDS
    assert "quit" in EXIT_COMMANDS
    assert "/q" in EXIT_COMMANDS


def test_cli_parser_has_chat_subcommand():
    """CLI parser includes chat subcommand with --model arg."""
    from hermes.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["chat"])
    assert args.command == "chat"
    assert args.model is None


def test_cli_parser_chat_model_arg():
    """Chat subcommand accepts --model argument."""
    from hermes.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["chat", "--model", "mistral:7b"])
    assert args.command == "chat"
    assert args.model == "mistral:7b"


@patch("hermes.agent.agent.check_ollama_connection", return_value=False)
def test_run_chat_ollama_not_running(mock_check, capsys):
    """run_chat prints helpful error when Ollama is unreachable."""
    from hermes.agent.tui import run_chat

    session = MagicMock()
    run_chat(session)

    mock_check.assert_called_once()
    # Function should return without entering the REPL loop


@patch("hermes.agent.agent.check_ollama_connection", return_value=True)
@patch("hermes.agent.agent.create_agent")
def test_run_chat_exit_command(mock_create_agent, mock_check):
    """run_chat exits cleanly when user types 'exit'."""
    from hermes.agent.tui import run_chat

    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    session = MagicMock()

    with patch("hermes.agent.tui.PromptSession") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt.prompt.return_value = "exit"
        mock_prompt_cls.return_value = mock_prompt

        run_chat(session)

    # Agent.run should NOT be called since user typed exit
    mock_agent.run.assert_not_called()


@patch("hermes.agent.agent.check_ollama_connection", return_value=True)
@patch("hermes.agent.agent.create_agent")
def test_run_chat_quit_command(mock_create_agent, mock_check):
    """run_chat exits cleanly when user types 'quit'."""
    from hermes.agent.tui import run_chat

    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    session = MagicMock()

    with patch("hermes.agent.tui.PromptSession") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt.prompt.return_value = "quit"
        mock_prompt_cls.return_value = mock_prompt

        run_chat(session)

    mock_agent.run.assert_not_called()


@patch("hermes.agent.agent.check_ollama_connection", return_value=True)
@patch("hermes.agent.agent.create_agent")
def test_run_chat_slash_q_command(mock_create_agent, mock_check):
    """run_chat exits cleanly when user types '/q'."""
    from hermes.agent.tui import run_chat

    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    session = MagicMock()

    with patch("hermes.agent.tui.PromptSession") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt.prompt.return_value = "/q"
        mock_prompt_cls.return_value = mock_prompt

        run_chat(session)

    mock_agent.run.assert_not_called()


@patch("hermes.agent.agent.check_ollama_connection", return_value=True)
@patch("hermes.agent.agent.create_agent")
def test_run_chat_empty_input_skipped(mock_create_agent, mock_check):
    """run_chat skips empty input and re-prompts."""
    from hermes.agent.tui import run_chat

    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    session = MagicMock()

    with patch("hermes.agent.tui.PromptSession") as mock_prompt_cls:
        mock_prompt = MagicMock()
        # First empty, then exit
        mock_prompt.prompt.side_effect = ["", "  ", "exit"]
        mock_prompt_cls.return_value = mock_prompt

        run_chat(session)

    mock_agent.run.assert_not_called()


@patch("hermes.agent.agent.check_ollama_connection", return_value=True)
@patch("hermes.agent.agent.create_agent")
def test_run_chat_keyboard_interrupt(mock_create_agent, mock_check):
    """run_chat handles KeyboardInterrupt gracefully."""
    from hermes.agent.tui import run_chat

    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    session = MagicMock()

    with patch("hermes.agent.tui.PromptSession") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt.prompt.side_effect = KeyboardInterrupt()
        mock_prompt_cls.return_value = mock_prompt

        # Should not raise
        run_chat(session)


@patch("hermes.agent.agent.check_ollama_connection", return_value=True)
@patch("hermes.agent.agent.create_agent")
def test_run_chat_eof_error(mock_create_agent, mock_check):
    """run_chat handles EOFError (Ctrl+D) gracefully."""
    from hermes.agent.tui import run_chat

    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    session = MagicMock()

    with patch("hermes.agent.tui.PromptSession") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt.prompt.side_effect = EOFError()
        mock_prompt_cls.return_value = mock_prompt

        # Should not raise
        run_chat(session)


@patch("hermes.agent.agent.check_ollama_connection", return_value=True)
@patch("hermes.agent.agent.create_agent")
def test_run_chat_agent_error_handled(mock_create_agent, mock_check):
    """run_chat catches agent errors and continues the loop."""
    from hermes.agent.tui import run_chat

    mock_agent = MagicMock()
    mock_agent.run.side_effect = [RuntimeError("LLM error"), None]
    mock_create_agent.return_value = mock_agent

    session = MagicMock()

    with patch("hermes.agent.tui.PromptSession") as mock_prompt_cls:
        mock_prompt = MagicMock()
        # First query triggers error, second succeeds, third exits
        mock_prompt.prompt.side_effect = ["test query", "another query", "exit"]
        mock_prompt_cls.return_value = mock_prompt

        # Should not raise despite agent error
        run_chat(session)

    assert mock_agent.run.call_count == 2


def test_looks_like_markdown():
    """Markdown detection heuristic works for common patterns."""
    from hermes.agent.tui import _looks_like_markdown

    assert _looks_like_markdown("# Header")
    assert _looks_like_markdown("- item 1")
    assert _looks_like_markdown("| col1 | col2 |")
    assert _looks_like_markdown("**bold text**")
    assert not _looks_like_markdown("plain text no formatting")
    assert not _looks_like_markdown("just a sentence.")
