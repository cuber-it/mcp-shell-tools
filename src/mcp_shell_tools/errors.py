"""The refusals the tools raise.

Every refusal is a :class:`ToolError`, so a caller tells a deliberate refusal
from a crash by the class alone.
"""


class ToolError(Exception):
    """A tool refused to do what it was asked."""


class OutsideBoundaryError(ToolError):
    """The path lies outside what this installation may touch."""


class NotPermittedError(ToolError):
    """The mode this installation runs in does not permit the action."""
