# Tool reference

Thirty-three tools in eight groups. All of them share one workspace: a change of
working directory, a note or an environment variable holds for every client of
the same server until it is changed again or the server restarts.

Paths may be relative to the working directory, absolute, or start with `~`.
Every result is text. Output longer than 200 000 characters and listings longer
than 200 rows are cut, and the cut says how much was left out. Which access a
tool needs is listed in [boundary](boundary.md).

Directories that never help in a search are skipped below the starting point:
`.git`, `__pycache__`, `.venv`, `node_modules`, `.mypy_cache`.

## Files

### `file_read`

`file_read(path, start=0, end=0)`

Returns the text of a file. `start` and `end` select lines, both counted from 1
and inclusive; `0` means the start or the end of the file. A file that is not
UTF-8 text is refused.

### `file_write`

`file_write(path, content)`

Writes text to a file and replaces what was there. Missing parent directories
are created.

### `file_append`

`file_append(path, content)`

Adds text to the end of a file and creates it if it does not exist.

### `file_list`

`file_list(path=".")`

Lists a directory, directories first, files with their size in bytes.

### `file_delete`

`file_delete(path)`

Moves a file or a directory with everything below it into the trash in the
state directory, named `<YYYYmmdd-HHMMSS-micro>-<name>`. The answer names where
it went; `file_move` brings it back. A symlink is moved itself, not what it
points to. Without a state directory deleting is refused.

### `file_move`

`file_move(source, destination)`

Moves or renames a file or directory; a symlink is moved itself. Missing parent
directories of the destination are created.

### `file_copy`

`file_copy(source, destination)`

Copies a file, or a directory with everything below it. Symlinks inside a copied
directory are copied as links.

### `tree`

`tree(path=".", depth=3)`

Shows a directory and what is below it down to `depth` levels, directories
first. Skipped directories and entries leading outside the boundary are left
out.

## Looking at a file

### `file_info`

`file_info(path)`

Reports kind, size, permissions, owner and the modification, access and change
times; for a directory also the number of entries; for a symlink its target.

### `head`

`head(path, lines=10)`

Returns the first lines of a text file, at least one.

### `tail`

`tail(path, lines=10)`

Returns the last lines of a text file, at least one.

## Editing

### `str_replace`

`str_replace(path, old, new)`

Replaces a passage that appears exactly once. No match and several matches are
both refused, and the file stays as it was.

### `diff_preview`

`diff_preview(path, content)`

Shows a unified diff of what writing `content` would change, without writing.
For a file that does not exist yet the diff shows all of `content`.

### `find_replace`

`find_replace(old, new, path=".", glob="*", apply=False)`

Replaces a passage in every file whose name matches `glob`, in `path` and all
directories below it. Without `apply` nothing is written: the answer lists the
files and how often each matches. Symlinks and files that are not UTF-8 text
are passed over. The run stops after 200 affected files and says so. When a
write fails, the message says how many files before it were already changed.

## Finding

### `glob_search`

`glob_search(pattern, path=".")`

Finds files whose path below `path` matches a glob pattern; `**` descends into
subdirectories, as in `**/*.py`. An empty or absolute pattern is refused.

### `grep`

`grep(pattern, path=".", glob="**/*")`

Finds lines matching a regular expression, in a single file or in the files
below a directory that match `glob`. Each hit reads `file:line: text`. Files
that are not UTF-8 text are passed over.

## Commands and environment

### `exec`

`exec(command, timeout=0)`

Runs a shell command in the working directory. Standard output and standard
error come back together; a non-zero exit status is appended as
`[exit status N]`, and a command without output answers `[no output]`.
`timeout` in seconds replaces the default of 120; a command that runs longer is
stopped and refused. Refused while commands are switched off.

### `env`

`env(name="")`

Returns one environment variable as `NAME=value`, or all of them sorted. An
unset name is refused.

### `which`

`which(name)`

Says where a command is found on the current `PATH`.

### `set_env`

`set_env(name, value)`

Sets an environment variable for the commands that follow, until the server
restarts. A name that is empty, contains `=` or starts with a digit is refused.

## Where work happens

### `cwd`

`cwd()`

Returns the working directory.

### `cd`

`cd(path)`

Changes the working directory for every tool and every client of the server.

### `project_context`

`project_context(path=".")`

Returns the `CLAUDE.md` of a directory, cut after 4000 characters, or says there
is none.

## Notes and sessions

### `memory_add`

`memory_add(note)`

Keeps a note with a UTC time stamp for as long as the server runs. An empty
note is refused.

### `memory_show`

`memory_show()`

Returns the notes, oldest first.

### `memory_clear`

`memory_clear()`

Drops every note and says how many there were.

### `session_save`

`session_save(name, summary="")`

Writes the notes and the working directory to `<name>.session.json` in the
state directory. A name that is empty, contains `/` or starts with `.` is
refused.

### `session_resume`

`session_resume(name)`

Restores the notes and the working directory of a saved session. Everything is
checked before anything is restored, so a refusal leaves the workspace as it
was.

### `session_list`

`session_list()`

Lists the saved sessions with their summaries, most recently saved first.

## The machine

### `ps`

`ps(name="")`

Lists processes with PID, user, resident memory and name, biggest first.
`name` keeps only processes whose name contains it, ignoring case. There is no
CPU column.

### `sysinfo`

`sysinfo()`

Reports system, host, Python version, CPU cores and threads, memory, swap, the disk
holding the working directory, uptime and load averages.

### `port_check`

`port_check(port=0)`

Lists listening TCP and UDP sockets with address, port, PID and process name;
with `port` only that one. Refused when the operating system does not let the
server read the sockets.

### `disk_usage`

`disk_usage(path=".", depth=1)`

Reports free and used space of the filesystem, then the size of the
subdirectories down to `depth` levels, biggest first. Symlinks are not followed.
