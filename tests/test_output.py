"""Reading text, and keeping output within its limits."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_shell_tools import ToolError
from mcp_shell_tools.output import cut, read_text, render, size, span, text_or_none


def test_short_text_is_left_alone() -> None:
    assert cut("hello", 10) == "hello"


def test_long_text_is_cut_and_says_so() -> None:
    shortened = cut("x" * 25, 10)

    assert shortened.startswith("x" * 10)
    assert shortened.endswith("[... 15 more characters]")


def test_text_at_the_limit_is_not_cut() -> None:
    assert cut("12345", 5) == "12345"


def test_rows_are_joined_within_the_limit() -> None:
    assert render(["a"], 5, "nothing") == "a"


def test_rows_beyond_the_limit_are_counted() -> None:
    assert render(["a", "b", "c"], 2, "nothing") == "a\nb\n[... 1 more]"


def test_no_rows_give_the_empty_line() -> None:
    assert render([], 5, "nothing") == "nothing"


@pytest.mark.parametrize(
    ("seconds", "shown"),
    [
        (-5, "0m"),
        (59, "0m"),
        (61, "1m"),
        (3 * 3600 + 300, "3h 5m"),
        (90061, "1d 1h 1m"),
    ],
)
def test_a_span_is_rendered_in_days_hours_and_minutes(seconds: int, shown: str) -> None:
    assert span(seconds) == shown


def test_sizes_are_rendered_in_every_unit() -> None:
    assert size(500) == "500B"
    assert size(2_000_000) == "1.9M"
    assert size(3.5e12).endswith("T")


def test_reading_returns_the_text(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")

    assert read_text(tmp_path / "a.txt") == "hello"


def test_reading_a_missing_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="no such file"):
        read_text(tmp_path / "nowhere.txt")


def test_reading_a_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="this is a directory"):
        read_text(tmp_path)


def test_reading_something_that_is_not_text_is_refused(tmp_path: Path) -> None:
    (tmp_path / "binary").write_bytes(b"\xff\xfe\x00\x01")

    with pytest.raises(ToolError, match="not text"):
        read_text(tmp_path / "binary")


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads unreadable files")
def test_reading_an_unreadable_file_is_refused_in_words(tmp_path: Path) -> None:
    locked = tmp_path / "locked.txt"
    locked.write_text("x", encoding="utf-8")
    locked.chmod(0)

    with pytest.raises(ToolError, match="could not read"):
        read_text(locked)


def test_lenient_reading_returns_the_text(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")

    assert text_or_none(tmp_path / "a.txt") == "hello"


def test_lenient_reading_passes_over_what_is_not_text(tmp_path: Path) -> None:
    (tmp_path / "binary").write_bytes(b"\xff\xfe\x00\x01")

    assert text_or_none(tmp_path / "binary") is None
    assert text_or_none(tmp_path / "nowhere") is None
