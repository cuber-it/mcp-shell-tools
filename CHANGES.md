# Changes

## 5.1.0

- A standalone server and a command line, on the same tools.

  `server.py` serves the whole set over stdio or HTTP. It is the only module
  that imports the MCP SDK, and the SDK is an optional extra: `pip install
  "mcp-shell-tools[server]"`. Everything below it stays free of the protocol,
  which is what lets the same module be a plugin, a server and a library.

  `cli.py` runs the tools from a shell. It does not list them: it asks the
  plugin what it publishes and builds a subcommand per tool from the
  signature, so a tool added in `shell.py` is on the command line at once.
  Paths keep their place on the line, numbers and switches are flags.

  The entry point `mcp-shell-tools` is the command line now, with `serve` as
  its first subcommand. The note that 5.0 left in its place is gone, because
  there is a server again.

## 5.0.2

- Republished under a new number.

  5.0.0 and 5.0.1 were withdrawn from PyPI, and a withdrawn number cannot be
  uploaded again. The 4.x releases are gone as well, so the README no longer
  offers them as a fallback.

## 5.0.1

- The command from version 4 answers again, with an explanation.

  Version 4 installed `mcp-shell-tools` as a standalone server. Version 5 is a
  plugin and has none, so the command vanished and every client configured
  against it failed with "command not found" and no reason. It exists again
  and says what happened, how to stay on the old line, and how to load the
  plugin instead. It exits non-zero, because it is not a server.

- The README leads with what changed, not with the plugin interface.

  Someone arriving from version 4 needs the break first: no standalone server,
  Python 3.12 instead of 3.10, `command` gone, and the git, http, pip and
  systemd tools in their own packages since 4.0.

## 5.0.0

- Seven findings from a review of the whole package, fixed.

  `find_replace` walked into `.git` and `.venv` and rewrote what it found
  there. It now skips the same directories the search tools skip, and the list
  lives in one place instead of two.

  Cutting a long result and saying how much was left out existed six times in
  three wordings, one of them broken: the tree could only ever report one
  entry too many, however many it had dropped. There is one `render` now.

  `session_resume` set the working directory straight from the saved file,
  which let a session move the workspace out of `allowed_roots`. It goes
  through `resolve` now.

  `disk_usage` measured every directory on its own, reading the deep files
  once per level above them. One walk now, adding each file to its ancestors.

  `ps` had a CPU column that was always 0.0 because a share needs two readings
  and a listing takes one. The column is gone rather than wrong.

  A failed copy said "could not copie": a verb built by chopping the last
  letter off "copied". And `_size` had a branch after the loop that nothing
  could reach.

- The docstring boilerplate is gone.

  Every function carried an `Args` block repeating its own signature, and
  twenty `Returns` blocks said what the summary line had already said. What
  remains states the output format, where a limit cuts, and what a refusal
  means.

- The dependency on `mcp` is gone.

  The package never imported it; ruff forbids it and `CLAUDE.md` explains why.
  Declaring it anyway said the opposite. `psutil` is the only dependency.

- The tools that 4.0.2 had and this rewrite lacked are back.

  `file_info`, `head` and `tail` for looking at a single file. `find_replace`
  for a change across many files, which writes nothing until `apply` is true.
  `which` for finding a command on the PATH. And the machine group that was
  missing entirely: `ps`, `sysinfo`, `port_check`, `disk_usage`.

  The machine tools use `psutil`, the package's first runtime dependency.
  Reading processes, memory and listening sockets through `/proc` by hand
  would tie the package to Linux for no gain.

  That brings the set to thirty-three tools in eight groups. Nothing published
  by 4.0.2 is missing now except `command`, which stays out for the reason
  given below.

- Repository created with the full tool set.

  Twenty-four tools in six groups, published through the proxy's registrar.
  The package depends on nothing: a plugin is handed its registrar and has no
  business importing the SDK, which ruff enforces.

  Deliberately left out: `command` from the old set. It steered logging and
  transcripts of the old server; rebuilding it would mean inventing a logging
  concept that is noted but not commissioned. `project_init` became
  `project_context`, which reads a directory's CLAUDE.md instead of writing a
  template.
