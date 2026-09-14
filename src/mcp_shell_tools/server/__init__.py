"""The MCP server on top of the library.

:mod:`.registry` binds the tools to a workspace and hands them out as a plain
catalogue, by name. It knows no server and imports no SDK, so any server can
publish that catalogue. :mod:`.app` is the one that does it with the MCP SDK,
and the only module importing it.
"""
