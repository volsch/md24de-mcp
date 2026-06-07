from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture


def test_main_default_log_level(mocker: MockerFixture) -> None:
    mock_run = mocker.patch("md24de_mcp.server.mcp.run")
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("LOG_LEVEL", None)
        from md24de_mcp import main
        main()
    mock_run.assert_called_once()


def test_main_warning_level_silences_httpx(mocker: MockerFixture) -> None:
    mock_run = mocker.patch("md24de_mcp.server.mcp.run")
    mock_set = mocker.patch("logging.Logger.setLevel")
    with patch.dict("os.environ", {"LOG_LEVEL": "WARNING"}):
        from md24de_mcp import main
        main()
    mock_run.assert_called_once()
    # httpx logger should be set to WARNING when log_level > DEBUG
    httpx_calls = [
        c for c in mock_set.call_args_list if c.args == (logging.WARNING,)
    ]
    assert httpx_calls


def test_main_debug_level_does_not_suppress_httpx(mocker: MockerFixture) -> None:
    mock_run = mocker.patch("md24de_mcp.server.mcp.run")
    httpx_warning_set = []

    original_set_level = logging.Logger.setLevel

    def tracking_set_level(self: logging.Logger, level: int) -> None:
        if self.name == "httpx" and level == logging.WARNING:
            httpx_warning_set.append(True)
        original_set_level(self, level)

    mocker.patch("logging.Logger.setLevel", tracking_set_level)
    with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}):
        from md24de_mcp import main
        main()
    mock_run.assert_called_once()
    assert not httpx_warning_set  # httpx should NOT be silenced at DEBUG level


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR"])
def test_main_accepts_all_standard_levels(mocker: MockerFixture, level: str) -> None:
    mocker.patch("md24de_mcp.server.mcp.run")
    with patch.dict("os.environ", {"LOG_LEVEL": level}):
        from md24de_mcp import main
        main()  # should not raise
