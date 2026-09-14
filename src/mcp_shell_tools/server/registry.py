"""The tools as a catalogue a server can publish.

:func:`catalogue` binds every tool to one shared workspace and returns them by
the name they are published under. It knows no server and imports no SDK:
whatever publishes the catalogue, the MCP SDK in :mod:`.app` or a server
library of our own, takes it from here.

The functions below are thin on purpose: each binds the workspace and hands the
work to a module that knows nothing about MCP. **The docstring of a wrapper is
the description that lands in the client's catalogue** — it is read, not
merely stored. Its signature becomes the input schema.

Names carry no prefix. Putting one in front is the publisher's business.
"""

from __future__ import annotations

from collections.abc import Callable

from mcp_shell_tools import edit, files, find, notes, place, run, system
from mcp_shell_tools.workspace import Workspace

Tool = Callable[..., str]
Catalogue = dict[str, Tool]


def catalogue(space: Workspace) -> Catalogue:
    """Return every tool bound to the workspace, by its published name."""
    return {
        **_files(space),
        **_inspecting(space),
        **_editing(space),
        **_finding(space),
        **_running(space),
        **_place(space),
        **_notes(space),
        **_system(space),
    }


def _named(*tools: Tool) -> Catalogue:
    """Key each tool by its own function name."""
    return {tool.__name__: tool for tool in tools}


def _files(space: Workspace) -> Catalogue:
    """Bind the tools that read and move files."""

    def file_read(path: str, start: int = 0, end: int = 0) -> str:
        """Read a text file and return its content.

        Give start and end to read a range of lines, both 1-based and
        inclusive; leave them at 0 for the whole file. Long content is cut at
        the configured limit, which is said in the output.

        Auf Deutsch: Datei lesen, öffnen, anzeigen, Inhalt ansehen, Quelltext.
        """
        return files.file_read(space, path, start, end)

    def file_write(path: str, content: str) -> str:
        """Write text to a file, replacing whatever was there.

        Missing parent directories are created. Prefer this over echoing into
        a file from a shell command: a heredoc inside a long command line is
        where quoting goes wrong.

        Auf Deutsch: Datei schreiben, speichern, anlegen, überschreiben, Text ablegen.
        """
        return files.file_write(space, path, content)

    def file_append(path: str, content: str) -> str:
        """Add text to the end of a file, creating it if it does not exist.

        Auf Deutsch: an Datei anhängen, ergänzen, hinzufügen, Zeile anfügen.
        """
        return files.file_append(space, path, content)

    def file_list(path: str = ".") -> str:
        """List a directory, directories first, with file sizes.

        Auf Deutsch: Verzeichnis auflisten, Ordner anzeigen, Inhalt, was liegt hier.
        """
        return files.file_list(space, path)

    def file_delete(path: str) -> str:
        """Delete a file, or a directory with everything below it.

        There is no undo. Check with file_list first if unsure.

        Auf Deutsch: Datei löschen, entfernen, Verzeichnis wegräumen.
        """
        return files.file_delete(space, path)

    def file_move(source: str, destination: str) -> str:
        """Move or rename a file or directory.

        Auf Deutsch: Datei verschieben, umbenennen, Ordner verlegen.
        """
        return files.file_move(space, source, destination)

    def file_copy(source: str, destination: str) -> str:
        """Copy a file, or a directory with everything below it.

        Symlinks inside a copied directory stay links.

        Auf Deutsch: Datei kopieren, duplizieren, Ordner kopieren, Sicherung.
        """
        return files.file_copy(space, source, destination)

    def tree(path: str = ".", depth: int = 3) -> str:
        """Show a directory and what is below it, down to the given depth.

        Directories that never help — .git, __pycache__, .venv, node_modules —
        are left out.

        Auf Deutsch: Verzeichnisbaum, Struktur anzeigen, Ordnerstruktur, Übersicht.
        """
        return files.tree(space, path, depth)

    return _named(
        file_read,
        file_write,
        file_append,
        file_list,
        file_delete,
        file_move,
        file_copy,
        tree,
    )


def _inspecting(space: Workspace) -> Catalogue:
    """Bind the tools that look at a single file without changing it."""

    def file_info(path: str) -> str:
        """Report what is known about a file: size, rights, owner, times.

        Auf Deutsch: Dateiinfo, Eigenschaften, wie groß, wem gehört, wann geändert.
        """
        return files.file_info(space, path)

    def head(path: str, lines: int = 10) -> str:
        """Return the first lines of a file.

        Auf Deutsch: Anfang der Datei, erste Zeilen, Kopf, oben.
        """
        return files.head(space, path, lines)

    def tail(path: str, lines: int = 10) -> str:
        """Return the last lines of a file.

        Useful on a log, where what matters is at the end.

        Auf Deutsch: Ende der Datei, letzte Zeilen, Schluss, unten, Logdatei.
        """
        return files.tail(space, path, lines)

    return _named(file_info, head, tail)


def _editing(space: Workspace) -> Catalogue:
    """Bind the tools that change text in place."""

    def str_replace(path: str, old: str, new: str) -> str:
        """Replace one passage in a file with another.

        The passage must appear exactly once. No match or several matches are
        refused rather than guessed, because both mean the caller and the file
        disagree about what is there.

        Auf Deutsch: Text ersetzen, ändern, austauschen, Stelle bearbeiten.
        """
        return edit.str_replace(space, path, old, new)

    def diff_preview(path: str, content: str) -> str:
        """Show what writing this content would change, without writing it.

        Returns a unified diff against the file as it is now.

        Auf Deutsch: Änderung vorab ansehen, Vorschau, Unterschied, Diff.
        """
        return edit.diff_preview(space, path, content)

    def find_replace(
        old: str,
        new: str,
        path: str = ".",
        glob: str = "*",
        apply: bool = False,
    ) -> str:
        """Replace a passage across many files, dry run by default.

        Nothing is written until apply is true, so the change can be read
        before it happens. The run stops at the result limit and says so.

        Auf Deutsch: überall ersetzen, in allen Dateien ändern, Massenersetzung.
        """
        return edit.find_replace(space, old, new, path, glob, apply=apply)

    return _named(str_replace, diff_preview, find_replace)


def _finding(space: Workspace) -> Catalogue:
    """Bind the tools that look for files and for text."""

    def glob_search(pattern: str, path: str = ".") -> str:
        """Find files whose path matches a glob pattern.

        Use ** to descend into subdirectories, for instance **/*.py.

        Auf Deutsch: Dateien suchen, finden, nach Namen, Muster, Dateiendung.
        """
        return find.glob_search(space, pattern, path)

    def grep(pattern: str, path: str = ".", glob: str = "**/*") -> str:
        """Find lines matching a regular expression.

        Returns file, line number and the line itself. Narrow the search with
        glob when a directory is large.

        Auf Deutsch: Text suchen, in Dateien finden, Vorkommen, Suchbegriff, Muster.
        """
        return find.grep(space, pattern, path, glob)

    return _named(glob_search, grep)


def _running(space: Workspace) -> Catalogue:
    """Bind the tools that run commands."""

    def run_command(command: str, timeout: float = 0) -> str:
        """Run a shell command in the working directory.

        Standard output and standard error come back together, and a non-zero
        exit status is named, so a failure cannot be mistaken for silence.
        Give timeout in seconds to override the configured default.

        Auf Deutsch: Befehl ausführen, Kommando, Shell, Terminal, aufrufen, starten.
        """
        return run.shell_exec(space, command, timeout)

    def env(name: str = "") -> str:
        """Show the environment the commands run in, or one variable of it.

        Auf Deutsch: Umgebungsvariablen anzeigen, Umgebung, Variable auslesen.
        """
        return run.env(space, name)

    def which(name: str) -> str:
        """Report where a command is found, following the current PATH.

        Auf Deutsch: wo liegt der Befehl, Pfad zum Programm, ist es installiert.
        """
        return run.which(space, name)

    def set_env(name: str, value: str) -> str:
        """Set an environment variable for the commands that follow.

        It holds as long as the server runs and is gone after a restart.

        Auf Deutsch: Umgebungsvariable setzen, Variable belegen.
        """
        return run.set_env(space, name, value)

    # Published as "exec"; the function is named differently so it does not
    # shadow the built-in of that name.
    return {"exec": run_command, **_named(env, which, set_env)}


def _place(space: Workspace) -> Catalogue:
    """Bind the tools about where work happens."""

    def cwd() -> str:
        """Return the directory the tools are working in.

        Auf Deutsch: aktuelles Verzeichnis, wo bin ich, Arbeitsverzeichnis.
        """
        return place.cwd(space)

    def cd(path: str) -> str:
        """Change the directory the tools work in.

        It holds for every tool from here on, until it is changed again or the
        server restarts.

        Auf Deutsch: Verzeichnis wechseln, hingehen, Arbeitsverzeichnis ändern.
        """
        return place.cd(space, path)

    def project_context(path: str = ".") -> str:
        """Return what a directory's CLAUDE.md says, if there is one.

        Auf Deutsch: Projektregeln lesen, Projektkontext, Anweisungen, CLAUDE.md.
        """
        return place.project_context(space, path)

    return _named(cwd, cd, project_context)


def _notes(space: Workspace) -> Catalogue:
    """Bind the tools that remember things."""

    def memory_add(note: str) -> str:
        """Keep a note for the rest of this server's run.

        Notes live in the process and are gone after a restart. Use
        session_save to keep something beyond that.

        Auf Deutsch: Notiz machen, merken, festhalten, Erkenntnis speichern.
        """
        return notes.memory_add(space, note)

    def memory_show() -> str:
        """Return the notes kept so far, oldest first.

        Auf Deutsch: Notizen anzeigen, was habe ich gemerkt, Merkliste.
        """
        return notes.memory_show(space)

    def memory_clear() -> str:
        """Drop every note kept so far.

        Auf Deutsch: Notizen löschen, Merkliste leeren, vergessen.
        """
        return notes.memory_clear(space)

    def session_save(name: str, summary: str = "") -> str:
        """Write the current notes and working directory to disk under a name.

        Auf Deutsch: Sitzung speichern, Stand sichern, Arbeitsstand ablegen.
        """
        return notes.session_save(space, name, summary)

    def session_resume(name: str) -> str:
        """Load a saved session: its notes and its working directory.

        Auf Deutsch: Sitzung fortsetzen, laden, Stand wiederherstellen.
        """
        return notes.session_resume(space, name)

    def session_list() -> str:
        """List the saved sessions, most recently saved first.

        Auf Deutsch: Sitzungen auflisten, gespeicherte Stände anzeigen.
        """
        return notes.session_list(space)

    return _named(
        memory_add,
        memory_show,
        memory_clear,
        session_save,
        session_resume,
        session_list,
    )


def _system(space: Workspace) -> Catalogue:
    """Bind the tools that look at the machine itself."""

    def ps(name: str = "") -> str:
        """List running processes, biggest by memory first.

        Give a name to see only the processes whose name contains it.

        Auf Deutsch: laufende Prozesse, was läuft gerade, Prozessliste, Programme.
        """
        return system.ps(space, name)

    def sysinfo() -> str:
        """Report the machine: system, CPU, memory, disk, uptime, load.

        Auf Deutsch: Systeminfo, Rechner, Arbeitsspeicher, Auslastung, Laufzeit.
        """
        return system.sysinfo(space)

    def port_check(port: int = 0) -> str:
        """Say what listens on a port, or list everything that listens.

        Auf Deutsch: Port belegt, wer horcht, offene Ports, Dienst auf Port.
        """
        return system.port_check(space, port)

    def disk_usage(path: str = ".", depth: int = 1) -> str:
        """Report how much space a directory and its subdirectories take.

        Auf Deutsch: Speicherplatz, wie voll, Plattenbelegung, was ist groß.
        """
        return system.disk_usage(space, path, depth)

    return _named(ps, sysinfo, port_check, disk_usage)
