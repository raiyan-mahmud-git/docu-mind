from types import SimpleNamespace

from typer.testing import CliRunner

from documind.cli import app


class FakeRuntime:
    def __init__(self) -> None:
        self.registry = SimpleNamespace(list_documents=lambda: [])
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_list_command_shows_empty_state(monkeypatch) -> None:
    runtime = FakeRuntime()
    monkeypatch.setattr("documind.cli._make_runtime", lambda: runtime)
    result = CliRunner().invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No documents indexed." in result.output
    assert runtime.closed is True


def test_cli_help_lists_phase_four_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert all(name in result.output for name in ["ingest", "search", "list", "delete"])
