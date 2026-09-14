"""The tools as a catalogue a server can publish.

:func:`catalogue` binds every tool to one shared workspace and returns them by
the name they are published under. It knows no server and imports no SDK:
whatever publishes the catalogue, the MCP SDK in :mod:`.app` or a server
library of our own, takes it from here.

The functions below are thin on purpose: each binds the workspace and hands the
work to a module that knows nothing about MCP. **The docstring of a wrapper is
the description that lands in the client's catalogue** — it is read, not
merely stored. Its signature becomes the input schema. Each description has an
English paragraph, a German one, and a closing line of German search words.

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

        Liest eine Textdatei und gibt ihren Inhalt zurück. Mit start und end
        wird ein Zeilenbereich gelesen, beide ab 1 gezählt und einschließlich;
        bei 0 die ganze Datei. Langer Inhalt wird am eingestellten Limit
        gekürzt, das steht dann in der Ausgabe.

        Stichworte: Datei lesen, öffnen, anzeigen, Inhalt ansehen, Quelltext.
        """
        return files.file_read(space, path, start, end)

    def file_write(path: str, content: str) -> str:
        """Write text to a file, replacing whatever was there.

        Missing parent directories are created. Prefer this over echoing into
        a file from a shell command.

        Schreibt Text in eine Datei und ersetzt, was dort stand. Fehlende
        Elternverzeichnisse werden angelegt. Besser als echo aus einem
        Shell-Befehl.

        Stichworte: Datei schreiben, speichern, anlegen, überschreiben, ablegen.
        """
        return files.file_write(space, path, content)

    def file_append(path: str, content: str) -> str:
        """Add text to the end of a file, creating it if it does not exist.

        Hängt Text an das Ende einer Datei an und legt sie an, wenn es sie
        nicht gibt.

        Stichworte: an Datei anhängen, ergänzen, hinzufügen, Zeile anfügen.
        """
        return files.file_append(space, path, content)

    def file_list(path: str = ".") -> str:
        """List a directory, directories first, with file sizes.

        Listet ein Verzeichnis auf, Verzeichnisse zuerst, mit Dateigrößen.

        Stichworte: Verzeichnis auflisten, Ordner anzeigen, was liegt hier.
        """
        return files.file_list(space, path)

    def file_delete(path: str) -> str:
        """Delete a file, or a directory with everything below it.

        It goes to the trash under the state directory, not away for good. The
        answer names where it went, and file_move brings it back. A symlink is
        deleted itself, not what it points to.

        Löscht eine Datei oder ein Verzeichnis mit allem darunter. Der Eintrag
        wandert in den Papierkorb im Zustandsverzeichnis und ist nicht
        endgültig weg. Die Antwort nennt, wohin; file_move holt ihn zurück. Ein
        Symlink wird selbst gelöscht, nicht sein Ziel.

        Stichworte: Datei löschen, entfernen, Verzeichnis wegräumen, Papierkorb.
        """
        return files.file_delete(space, path)

    def file_move(source: str, destination: str) -> str:
        """Move or rename a file or directory.

        Verschiebt eine Datei oder ein Verzeichnis oder benennt es um.

        Stichworte: Datei verschieben, umbenennen, Ordner verlegen.
        """
        return files.file_move(space, source, destination)

    def file_copy(source: str, destination: str) -> str:
        """Copy a file, or a directory with everything below it.

        Symlinks inside a copied directory stay links.

        Kopiert eine Datei oder ein Verzeichnis mit allem darunter. Symlinks in
        einem kopierten Verzeichnis bleiben Links.

        Stichworte: Datei kopieren, duplizieren, Ordner kopieren, Sicherung.
        """
        return files.file_copy(space, source, destination)

    def tree(path: str = ".", depth: int = 3) -> str:
        """Show a directory and what is below it, down to the given depth.

        Directories that never help — .git, __pycache__, .venv, node_modules —
        are left out.

        Zeigt ein Verzeichnis und was darunter liegt, bis zur angegebenen
        Tiefe. Verzeichnisse, die nie helfen — .git, __pycache__, .venv,
        node_modules — werden ausgelassen.

        Stichworte: Verzeichnisbaum, Struktur anzeigen, Ordnerstruktur.
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

        Berichtet, was über eine Datei bekannt ist: Größe, Rechte, Eigentümer,
        Zeitstempel.

        Stichworte: Dateiinfo, Eigenschaften, wie groß, wem gehört, wann geändert.
        """
        return files.file_info(space, path)

    def head(path: str, lines: int = 10) -> str:
        """Return the first lines of a file.

        Gibt die ersten Zeilen einer Datei zurück.

        Stichworte: Anfang der Datei, erste Zeilen, Kopf, oben.
        """
        return files.head(space, path, lines)

    def tail(path: str, lines: int = 10) -> str:
        """Return the last lines of a file.

        Useful on a log, where what matters is at the end.

        Gibt die letzten Zeilen einer Datei zurück. Nützlich bei einem Log, wo
        das Wichtige am Ende steht.

        Stichworte: Ende der Datei, letzte Zeilen, Schluss, unten, Logdatei.
        """
        return files.tail(space, path, lines)

    return _named(file_info, head, tail)


def _editing(space: Workspace) -> Catalogue:
    """Bind the tools that change text in place."""

    def str_replace(path: str, old: str, new: str) -> str:
        """Replace one passage in a file with another.

        The passage must appear exactly once; no match and several matches are
        both refused.

        Ersetzt eine Textstelle in einer Datei durch eine andere. Die Stelle
        muss genau einmal vorkommen; kein Treffer und mehrere Treffer werden
        abgelehnt.

        Stichworte: Text ersetzen, ändern, austauschen, Stelle bearbeiten.
        """
        return edit.str_replace(space, path, old, new)

    def diff_preview(path: str, content: str) -> str:
        """Show what writing this content would change, without writing it.

        Returns a unified diff against the file as it is now.

        Zeigt, was das Schreiben dieses Inhalts ändern würde, ohne zu
        schreiben. Liefert einen Unified Diff gegen die Datei, wie sie jetzt
        ist.

        Stichworte: Änderung vorab ansehen, Vorschau, Unterschied, Diff.
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

        Ersetzt eine Textstelle in vielen Dateien, standardmäßig als
        Probelauf. Geschrieben wird erst mit apply=true, so lässt sich die
        Änderung vorher lesen. Der Lauf endet am Ergebnislimit und sagt das.

        Stichworte: überall ersetzen, in allen Dateien ändern, Massenersetzung.
        """
        return edit.find_replace(space, old, new, path, glob, apply=apply)

    return _named(str_replace, diff_preview, find_replace)


def _finding(space: Workspace) -> Catalogue:
    """Bind the tools that look for files and for text."""

    def glob_search(pattern: str, path: str = ".") -> str:
        """Find files whose path matches a glob pattern.

        Use ** to descend into subdirectories, for instance **/*.py.

        Findet Dateien, deren Pfad auf ein Glob-Muster passt. Mit ** geht es
        in Unterverzeichnisse, etwa **/*.py.

        Stichworte: Dateien suchen, finden, nach Namen, Muster, Dateiendung.
        """
        return find.glob_search(space, pattern, path)

    def grep(pattern: str, path: str = ".", glob: str = "**/*") -> str:
        """Find lines matching a regular expression.

        Returns file, line number and the line itself. Narrow the search with
        glob when a directory is large.

        Findet Zeilen, auf die ein regulärer Ausdruck passt. Liefert Datei,
        Zeilennummer und die Zeile selbst. Bei großen Verzeichnissen die Suche
        mit glob eingrenzen.

        Stichworte: Text suchen, in Dateien finden, Vorkommen, Suchbegriff.
        """
        return find.grep(space, pattern, path, glob)

    return _named(glob_search, grep)


def _running(space: Workspace) -> Catalogue:
    """Bind the tools that run commands."""

    def run_command(command: str, timeout: float = 0) -> str:
        """Run a shell command in the working directory.

        Standard output and standard error come back together, and a non-zero
        exit status is named. Give timeout in seconds to override the
        configured default. Commands are off unless the server was started
        with --exec or a grant switches them on; the refusal says how.

        Führt einen Shell-Befehl im Arbeitsverzeichnis aus. Standardausgabe und
        Fehlerausgabe kommen zusammen zurück, ein Exit-Status ungleich null
        wird genannt. timeout in Sekunden ersetzt den eingestellten Standard.
        Befehle sind aus, solange der Server nicht mit --exec gestartet wurde
        oder eine Freigabe sie einschaltet; die Ablehnung sagt, wie.

        Stichworte: Befehl ausführen, Kommando, Shell, Terminal, starten.
        """
        return run.shell_exec(space, command, timeout)

    def env(name: str = "") -> str:
        """Show the environment the commands run in, or one variable of it.

        Zeigt die Umgebung, in der Befehle laufen, oder eine Variable daraus.

        Stichworte: Umgebungsvariablen anzeigen, Umgebung, Variable auslesen.
        """
        return run.env(space, name)

    def which(name: str) -> str:
        """Report where a command is found, following the current PATH.

        Sagt, wo ein Befehl gefunden wird, nach dem aktuellen PATH.

        Stichworte: wo liegt der Befehl, Pfad zum Programm, ist es installiert.
        """
        return run.which(space, name)

    def set_env(name: str, value: str) -> str:
        """Set an environment variable for the commands that follow.

        It holds as long as the server runs and is gone after a restart.

        Setzt eine Umgebungsvariable für die folgenden Befehle. Sie gilt,
        solange der Server läuft, und ist nach einem Neustart weg.

        Stichworte: Umgebungsvariable setzen, Variable belegen.
        """
        return run.set_env(space, name, value)

    # Published as "exec"; the function is named differently so it does not
    # shadow the built-in of that name.
    return {"exec": run_command, **_named(env, which, set_env)}


def _place(space: Workspace) -> Catalogue:
    """Bind the tools about where work happens."""

    def cwd() -> str:
        """Return the directory the tools are working in.

        Gibt das Verzeichnis zurück, in dem die Werkzeuge arbeiten.

        Stichworte: aktuelles Verzeichnis, wo bin ich, Arbeitsverzeichnis.
        """
        return place.cwd(space)

    def cd(path: str) -> str:
        """Change the directory the tools work in.

        It holds for every tool from here on, until it is changed again or the
        server restarts.

        Wechselt das Verzeichnis, in dem die Werkzeuge arbeiten. Das gilt ab
        jetzt für jedes Werkzeug, bis es wieder geändert wird oder der Server
        neu startet.

        Stichworte: Verzeichnis wechseln, hingehen, Arbeitsverzeichnis ändern.
        """
        return place.cd(space, path)

    def project_context(path: str = ".") -> str:
        """Return what a directory's CLAUDE.md says, if there is one.

        Gibt zurück, was die CLAUDE.md eines Verzeichnisses sagt, falls es eine
        gibt.

        Stichworte: Projektregeln lesen, Projektkontext, Anweisungen, CLAUDE.md.
        """
        return place.project_context(space, path)

    return _named(cwd, cd, project_context)


def _notes(space: Workspace) -> Catalogue:
    """Bind the tools that remember things."""

    def memory_add(note: str) -> str:
        """Keep a note for the rest of this server's run.

        Notes live in the process and are gone after a restart. Use
        session_save to keep something beyond that.

        Hält eine Notiz für den Rest der Laufzeit dieses Servers fest. Notizen
        leben im Prozess und sind nach einem Neustart weg. Was darüber hinaus
        bleiben soll, gehört in session_save.

        Stichworte: Notiz machen, merken, festhalten, Erkenntnis speichern.
        """
        return notes.memory_add(space, note)

    def memory_show() -> str:
        """Return the notes kept so far, oldest first.

        Gibt die bisherigen Notizen zurück, die älteste zuerst.

        Stichworte: Notizen anzeigen, was habe ich gemerkt, Merkliste.
        """
        return notes.memory_show(space)

    def memory_clear() -> str:
        """Drop every note kept so far.

        Verwirft alle bisherigen Notizen.

        Stichworte: Notizen löschen, Merkliste leeren, vergessen.
        """
        return notes.memory_clear(space)

    def session_save(name: str, summary: str = "") -> str:
        """Write the current notes and working directory to disk under a name.

        Schreibt die aktuellen Notizen und das Arbeitsverzeichnis unter einem
        Namen auf die Platte.

        Stichworte: Sitzung speichern, Stand sichern, Arbeitsstand ablegen.
        """
        return notes.session_save(space, name, summary)

    def session_resume(name: str) -> str:
        """Load a saved session: its notes and its working directory.

        Lädt eine gespeicherte Sitzung: ihre Notizen und ihr
        Arbeitsverzeichnis.

        Stichworte: Sitzung fortsetzen, laden, Stand wiederherstellen.
        """
        return notes.session_resume(space, name)

    def session_list() -> str:
        """List the saved sessions, most recently saved first.

        Listet die gespeicherten Sitzungen auf, die zuletzt gespeicherte
        zuerst.

        Stichworte: Sitzungen auflisten, gespeicherte Stände anzeigen.
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

        Listet laufende Prozesse auf, die größten nach Speicher zuerst. Mit
        name nur die Prozesse, deren Name ihn enthält.

        Stichworte: laufende Prozesse, was läuft gerade, Prozessliste.
        """
        return system.ps(space, name)

    def sysinfo() -> str:
        """Report the machine: system, CPU, memory, disk, uptime, load.

        Berichtet über den Rechner: System, CPU, Speicher, Platte, Laufzeit,
        Last.

        Stichworte: Systeminfo, Rechner, Arbeitsspeicher, Auslastung, Laufzeit.
        """
        return system.sysinfo(space)

    def port_check(port: int = 0) -> str:
        """Say what listens on a port, or list everything that listens.

        Sagt, was auf einem Port lauscht, oder listet alles, was lauscht.

        Stichworte: Port belegt, wer horcht, offene Ports, Dienst auf Port.
        """
        return system.port_check(space, port)

    def disk_usage(path: str = ".", depth: int = 1) -> str:
        """Report how much space a directory and its subdirectories take.

        Berichtet, wie viel Platz ein Verzeichnis und seine Unterverzeichnisse
        belegen.

        Stichworte: Speicherplatz, wie voll, Plattenbelegung, was ist groß.
        """
        return system.disk_usage(space, path, depth)

    return _named(ps, sysinfo, port_check, disk_usage)
