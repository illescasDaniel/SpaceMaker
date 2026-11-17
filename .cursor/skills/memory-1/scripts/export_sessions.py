#!/usr/bin/env python3
"""Export a project's agent sessions (Claude Code, Codex, opencode) to condensed, redacted Markdown.

Keeps only what the user and the assistant said to each other: no tool calls, tool output, reasoning or injected
instructions. One file per session, named <first date>-<session id prefix>.md. A file is rewritten only when its
session has grown, so the script is safe to run at the end of every session.

usage: export_sessions.py [--project DIR] [--out DIR] [--since YYYY-MM-DD] [--max-chars N] [--dry-run]
       export_sessions.py --claude-dir DIR ...   (moved project, or worktrees outside it; repeatable)
Prints one line per new or updated file; add those to sessions/INDEX.md.
In a git repository the sessions of all its worktrees are collected, and from a linked worktree the default --out is
the main checkout's memory/sessions (linked from the worktree when possible). The archive is kept out of git by a
`/sessions` line in memory/.gitignore, which the script adds when it is missing.
Standard library only; Python 3.9+.
"""
import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

HOME = Path.home()
CLAUDE_ROOT = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude")) / "projects"
CODEX_ROOT = Path(os.environ.get("CODEX_HOME", HOME / ".codex")) / "sessions"
OPENCODE_DB = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share") / "opencode" / "opencode.db"

# Injected context rather than conversation.
SKIP_PREFIXES = (
    "<command-", "<local-command", "<system-reminder", "<task-notification", "<environment_context",
    "<user_instructions", "<permissions instructions", "<user_shell_command", "# AGENTS.md instructions",
    "Caveat:", "This session is being continued", "[Request interrupted",
)

# Credential-shaped strings. Conservative: a false positive costs a few characters of context.
R = "[REDACTED]"
SECRET_PATTERNS = [  # (pattern, replacement)
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", R),
    (r"\b(?:sk|pk|rk)-(?:ant-|proj-|live-|test-)?[A-Za-z0-9_\-]{16,}", R),
    (r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}", R),
    (r"\bglpat-[A-Za-z0-9_\-]{20,}|\bhf_[A-Za-z0-9]{20,}|\bnpm_[A-Za-z0-9]{30,}|\bpypi-[A-Za-z0-9_\-]{30,}", R),
    (r"\bxox[abposr]-[A-Za-z0-9\-]{10,}|\bAKIA[0-9A-Z]{16}\b|\bAIza[0-9A-Za-z_\-]{30,}", R),
    (r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}", R),                 # JWT
    (r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=\-]{20,}", r"\1 " + R),
    (r"(?i)\b([a-z0-9_]*(?:password|passwd|secret|token|api[_-]?key|access[_-]?key)[a-z0-9_]*\s*[:=]\s*[\"']?)"
     r"(?!\[REDACTED)[^\s\"'`,;]{8,}", r"\1" + R),
    (r"(?i)\b([a-z][a-z0-9+.\-]*://[^\s:/@]+:)[^\s@/]{4,}@", r"\1" + R + "@"),             # user:pass@host
]
SECRET_PATTERNS = [(re.compile(p, re.S), r) for p, r in SECRET_PATTERNS]


def redact(text):
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def clip(text, limit):
    if limit and len(text) > limit:
        return text[:limit] + f"\n[... {len(text) - limit} more characters not exported]"
    return text


def claude_text(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def read_claude(path):
    """Yield (role, timestamp, text) from a Claude Code transcript; drops subagent, meta and tool turns."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if event.get("type") not in ("user", "assistant") or event.get("isSidechain") or event.get("isMeta"):
                continue
            text = claude_text((event.get("message") or {}).get("content")).strip()
            if text:
                yield event["type"], event.get("timestamp", ""), text


def codex_meta(path):
    with path.open(encoding="utf-8", errors="replace") as fh:
        for _, raw in zip(range(5), fh):
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if event.get("type") == "session_meta":
                return event.get("payload") or {}
    return {}


def read_codex(path):
    """Yield (role, timestamp, text) from a Codex rollout file; drops developer, reasoning and tool items."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            item = event.get("payload") or {}
            if event.get("type") != "response_item" or item.get("type") != "message":
                continue
            role = item.get("role")
            if role not in ("user", "assistant"):
                continue
            text = "\n".join(b.get("text", "") for b in item.get("content") or []
                             if isinstance(b, dict) and b.get("type") in ("input_text", "output_text")).strip()
            if text:
                yield role, event.get("timestamp", ""), text


def opencode_db(note=True):
    """Open opencode's database read-only, or return None (missing, locked or unreadable) with one short note."""
    if not OPENCODE_DB.is_file():
        return None
    try:
        return sqlite3.connect(OPENCODE_DB.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)
    except sqlite3.Error as err:
        if note:
            print(f"opencode: cannot open its database ({err}); skipped", file=sys.stderr)
        return None


def opencode_sessions(roots):
    """Return ids of opencode's own (not subagent) sessions whose working directory is inside the project or a worktree."""
    db = opencode_db()
    if not db:
        return []
    try:
        with db:
            rows = db.execute("SELECT id, directory FROM session_v2 WHERE parent_id IS NULL ORDER BY time_created").fetchall()
    except sqlite3.Error as err:
        print(f"opencode: cannot read its sessions ({err}); skipped", file=sys.stderr)
        return []
    finally:
        db.close()
    return [sid for sid, directory in rows if any(inside(directory, root) for root in roots)]


def read_opencode(sid, path):
    """Yield (role, timestamp, text) from an opencode session; drops reasoning, tool items and compaction summaries."""
    db = opencode_db(note=False)
    if not db:
        return
    try:
        with db:
            rows = db.execute("SELECT type, time_created, data FROM session_message WHERE session_id = ? "
                              "AND type IN ('user', 'assistant') ORDER BY seq", (sid,)).fetchall()
    except sqlite3.Error:
        return
    finally:
        db.close()
    for role, millis, raw in rows:
        try:
            data = json.loads(raw)
            if role == "user":
                text = data.get("text")
            else:
                text = "\n".join(b.get("text", "") for b in data.get("content") or []
                                 if isinstance(b, dict) and b.get("type") == "text")
            stamp = datetime.fromtimestamp(millis / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, AttributeError, TypeError, OverflowError, OSError):
            continue
        if isinstance(text, str) and text.strip():
            yield role, stamp, text.strip()


def claude_cwd(path):
    with path.open(encoding="utf-8", errors="replace") as fh:
        for _, raw in zip(range(50), fh):
            try:
                cwd = json.loads(raw).get("cwd")
            except (ValueError, AttributeError):
                continue
            if cwd:
                return cwd
    return None


def inside(cwd, project):
    return bool(cwd) and (Path(cwd) == project or project in Path(cwd).parents)


def git_out(project, *args):
    """Stdout of `git -C project args`, or None when git is missing, fails or is not a repository."""
    try:
        done = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def git_layout(project):
    """Return (in_repo, main checkout when project is a linked worktree else None, every worktree path of the repo)."""
    git_dir, common, top = (git_out(project, "rev-parse", *a) for a in (("--git-dir",), ("--git-common-dir",), ("--show-toplevel",)))
    if not (git_dir and common and top and Path(top).resolve() == project):
        return False, None, [project]
    git_dir, common = (Path(project, d).resolve() for d in (git_dir, common))  # relative answers are relative to project
    main = common.parent if git_dir != common and common.name == ".git" else None
    roots = [project] + [Path(line[9:]).resolve() for line in (git_out(project, "worktree", "list", "--porcelain") or "").splitlines()
                         if line.startswith("worktree ")]
    return True, main, list(dict.fromkeys(roots))


def link_archive(local, target):
    """Best effort: make a worktree's memory/sessions a symlink to the main checkout's archive."""
    try:
        if local.is_symlink() or (local.exists() and (not local.is_dir() or any(local.iterdir()))):
            return
        target.mkdir(parents=True, exist_ok=True)
        if local.exists():
            local.rmdir()
        local.parent.mkdir(parents=True, exist_ok=True)
        local.symlink_to(target, target_is_directory=True)
    except OSError as err:
        print(f"could not link {local} to {target} ({err}); sessions are still written there", file=sys.stderr)


def ensure_ignored(out):
    """Keep the archive out of git: a `/sessions` line in the memory folder's .gitignore (no slash at the end, so it
    also matches a symlink)."""
    gitignore = out.parent / ".gitignore"
    try:
        old = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if any(line.strip() in ("/sessions", "/sessions/", "sessions", "sessions/") for line in old.splitlines()):
            return
        gitignore.write_text(old + ("\n" if old and not old.endswith("\n") else "") + "/sessions\n", encoding="utf-8")
    except OSError as err:
        print(f"could not update {gitignore} ({err}); keep {out.name}/ out of git yourself", file=sys.stderr)


def find_sessions(project, claude_dirs, roots=None):
    roots = roots or [project]
    found = []
    if claude_dirs:
        found += [("claude", p, read_claude) for d in claude_dirs for p in sorted(Path(d).glob("*.jsonl"))]
    elif CLAUDE_ROOT.is_dir():
        # Claude Code keeps a project's sessions under its absolute path with every non-alphanumeric character as "-";
        # worktrees inside the project get sibling folders with a longer name. Confirm each by its recorded cwd.
        encoded = [re.sub(r"[^A-Za-z0-9]", "-", str(root)) for root in roots]
        for cdir in sorted(CLAUDE_ROOT.iterdir()):
            if any(cdir.name == enc or cdir.name.startswith(enc + "-") for enc in encoded):
                found += [("claude", p, read_claude) for p in sorted(cdir.glob("*.jsonl"))
                          if cdir.name in encoded or any(inside(claude_cwd(p), root) for root in roots)]
    if CODEX_ROOT.is_dir():
        for path in sorted(CODEX_ROOT.rglob("*.jsonl")):
            meta = codex_meta(path)
            # Codex stores each subagent and automatic review as its own rollout; only the user's own sessions count.
            if any(inside(meta.get("cwd"), root) for root in roots) and not (isinstance(meta.get("source"), dict) and "subagent" in meta["source"]):
                found.append(("codex", path, read_codex))
    found += [("opencode", OPENCODE_DB, partial(read_opencode, sid)) for sid in opencode_sessions(roots)]
    return found


def render(client, path, reader, max_chars):
    turns = []
    for role, stamp, text in reader(path):
        if text.startswith(SKIP_PREFIXES):
            continue
        turns.append((role, stamp, redact(clip(text, max_chars))))
    if not turns or not any(r == "user" for r, _, _ in turns):
        return None, None
    first, last = turns[0][1], turns[-1][1]
    # Claude Code ids are random UUIDs; Codex and opencode ids are time-ordered, so take their random tail instead.
    stem = reader.args[0] if client == "opencode" else path.stem  # an opencode session is a row, not a file
    sid = stem[:8] if client == "claude" else stem[-8:]
    name = f"{first[:10] or 'undated'}-{sid}.md"
    body = [f"# Session {stem} ({client})\n\n{first[:16].replace('T', ' ')} to {last[:16].replace('T', ' ')} UTC, "
            f"{len(turns)} messages. Tool calls and outputs are not exported.\n"]
    body += [f"### {role} {stamp[:16].replace('T', ' ')}\n{text}\n" for role, stamp, text in turns]
    return name, "\n".join(body)


# agentic-loadout:begin entire-code
# Entire checkpoints (--entire): this pass adds the sessions that only Entire has, such as ones the agent no longer
# keeps on disk, ones recorded on another machine, and clients the readers above do not know. It only reads git data
# (`git for-each-ref`, `git ls-tree`, `git cat-file`), needs no Entire CLI, never fetches, and never rewrites a session
# file that already exists. It uses the same redaction and the same output format as the readers above.
# Entire keeps a checkpoint either as one ref (refs/entire/checkpoints/<xx>/<id>, the default since Entire 0.10.0) or on
# the branch entire/checkpoints/v1 (older setups). Entire does not document that layout; an unknown one is skipped with
# a warning rather than guessed at.
ENTIRE_FORMAT = 1  # `v` of Entire's compact transcript.jsonl
ENTIRE_REFS = ("refs/entire/checkpoints/", "refs/heads/entire/checkpoints/v1", "refs/remotes/*/entire/checkpoints/v1")
# <checkpoint dir>/<session index>/<file>: refs keep the files at the tree root, the branch under <xx>/<rest>/.
ENTIRE_ENTRY = re.compile(r"^(?P<ckpt>(?:[^/]+/[^/]+/)?)(?P<n>\d+)/(?P<file>transcript\.jsonl|metadata\.json)$")


def entire_git(project, *args):
    try:
        return subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


class EntireBlobs:
    """One long-running `git cat-file --batch`, so thousands of checkpoints cost one process."""

    def __init__(self, project):
        self.proc = subprocess.Popen(["git", "-C", str(project), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def read(self, sha):
        self.proc.stdin.write(sha.encode() + b"\n")
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().split()
        if len(header) < 3 or header[1] != b"blob":
            return None
        data = self.proc.stdout.read(int(header[2]))
        self.proc.stdout.read(1)  # the newline git adds after each object
        return data

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def entire_candidates(project):
    """(refs, slots): every Entire ref, and a dict {ref, ckpt, n, transcript: (sha, size), metadata: sha} per stored session."""
    refs = entire_git(project, "for-each-ref", "--format=%(refname)", *ENTIRE_REFS).stdout.split()
    slots = []
    for ref in refs:
        found = {}
        for line in entire_git(project, "ls-tree", "-r", "-l", "--full-tree", ref).stdout.splitlines():
            meta, _, path = line.partition("\t")
            match = ENTIRE_ENTRY.match(path)
            if not match:
                continue
            _mode, _kind, sha, size = meta.split(None, 3)
            slot = found.setdefault((match["ckpt"], match["n"]), {"ref": ref, "ckpt": match["ckpt"], "n": match["n"]})
            slot["transcript" if match["file"] == "transcript.jsonl" else "metadata"] = (sha, int(size.strip() or 0))
        slots += [s for s in found.values() if "transcript" in s and "metadata" in s]
    return refs, slots


def entire_label(slot):
    """The checkpoint id, as `entire checkpoint explain` takes it."""
    if slot["ckpt"]:
        return slot["ckpt"].rstrip("/").replace("/", "")
    return slot["ref"].rsplit("/", 1)[-1]


def read_entire(data, warn):
    """Yield (role, timestamp, agent, text) from Entire's compact transcript (one JSON object per line)."""
    for raw in data.decode("utf-8", errors="replace").splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if event.get("v") != ENTIRE_FORMAT:
            warn(f"unsupported transcript format v={event.get('v')!r}")
            return
        if event.get("type") not in ("user", "assistant"):
            continue
        text = "\n".join(b["text"] for b in event.get("content") or []
                         if isinstance(b, dict) and isinstance(b.get("text"), str) and b.get("type") in (None, "text")).strip()
        if text:
            yield event["type"], event.get("ts", ""), event.get("agent", ""), text


def render_entire(slot, session_id, data, max_chars, warn):
    turns, agent = [], ""
    for role, stamp, agent_name, text in read_entire(data, warn):
        agent = agent or agent_name
        if text.startswith(SKIP_PREFIXES):
            continue
        turns.append((role, stamp, redact(clip(text, max_chars))))
    if not turns or not any(r == "user" for r, _, _ in turns):
        return None, None, None
    first, last = turns[0][1], turns[-1][1]
    # Same file names as the readers above: Claude Code ids by their first 8 characters, Codex ids by their last 8.
    sid = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", session_id)
    sid = sid[-8:] if agent == "codex" else sid[:8]
    name = f"{first[:10] or 'undated'}-{sid}.md"
    body = [f"# Session {session_id} ({agent or 'unknown'}, from Entire checkpoint {entire_label(slot)})\n\n"
            f"{first[:16].replace('T', ' ')} to {last[:16].replace('T', ' ')} UTC, {len(turns)} messages. "
            "Tool calls and outputs are not exported.\n"]
    body += [f"### {role} {stamp[:16].replace('T', ' ')}\n{text}\n" for role, stamp, text in turns]
    return name, sid, "\n".join(body)


def entire_gitignore(out):
    """Keep a fresh archive out of git like the template: a `/sessions` line in the memory folder's .gitignore."""
    if out.name != "sessions":
        return
    gitignore = out.parent / ".gitignore"
    old = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if any(line.strip() in ("/sessions", "/sessions/", "sessions", "sessions/") for line in old.splitlines()):
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    gitignore.write_text(old + ("\n" if old and not old.endswith("\n") else "") + "/sessions\n", encoding="utf-8")


def export_entire(project, out, since=None, max_chars=6000, dry_run=False, log=print, warn=None, planned=()):
    """Write the sessions only Entire has. Returns the counts, or None when the repository has no Entire refs."""
    warn = warn or (lambda m: print(f"warning: {m}", file=sys.stderr))
    refs, slots = entire_candidates(project)
    if not refs:
        return None
    counts = {"new": 0, "present": 0, "skipped": 0}
    if not slots:
        warn(f"found {len(refs)} Entire ref(s) but none has the expected layout (<n>/transcript.jsonl next to "
             "<n>/metadata.json); Entire may have changed how it stores checkpoints, so nothing was exported")
        return counts
    reader = EntireBlobs(project)
    try:
        # A session can have several checkpoints; each transcript.jsonl holds the whole session up to that commit,
        # so the biggest one is the most complete.
        best = {}
        for slot in slots:
            try:
                meta = json.loads(reader.read(slot["metadata"][0]) or b"{}")
            except ValueError:
                continue
            session_id = meta.get("session_id")
            if not session_id:
                warn(f"checkpoint {entire_label(slot)} has no session id; skipped")
                continue
            if session_id not in best or slot["transcript"][1] > best[session_id]["transcript"][1]:
                best[session_id] = slot
        for session_id, slot in sorted(best.items()):
            data = reader.read(slot["transcript"][0])
            label = entire_label(slot)
            name, sid, text = render_entire(slot, session_id, data or b"", max_chars, lambda m: warn(f"{label}: {m}"))
            if name is None or (since and name[:10] < since):
                counts["skipped"] += 1
                continue
            # The readers above may have written this session already, possibly under another date: keep that file.
            # `planned`: names the native pass just rendered; in a dry run they are not on disk yet.
            if ((out / name).exists() or (out.is_dir() and next(iter(out.glob(f"*-{sid}.md")), None) is not None)
                    or any(p == name or p.endswith(f"-{sid}.md") for p in planned)):
                counts["present"] += 1
                continue
            counts["new"] += 1
            if not dry_run:
                entire_gitignore(out)
                out.mkdir(parents=True, exist_ok=True)
                (out / name).write_text(text, encoding="utf-8")
            print(f"{'new':8} {out / name}  ({text.splitlines()[0].split('(')[-1].split(',')[0]}, {len(text) // 1024} KB)")
    finally:
        reader.close()
    return counts


def entire_main(project, out, args, planned=()):
    if entire_git(project, "rev-parse", "--git-dir").returncode != 0:
        print(f"--entire: {project} is not a git repository, so there are no Entire checkpoints to read", file=sys.stderr)
        return 1
    counts = export_entire(project, out, args.since, args.max_chars, args.dry_run, planned=planned)
    if counts is None:
        print(f"no Entire checkpoints found in {project} (none committed yet, or none fetched)", file=sys.stderr)
        return 1
    print("entire: " + ", ".join(f"{v} {k}" for k, v in counts.items()), file=sys.stderr)
    return 0
# agentic-loadout:end entire-code


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=".", help="project root whose sessions to export (default: .)")
    ap.add_argument("--out", help="output folder (default: memory/sessions, or the main checkout's when run in a "
                    "linked git worktree)")
    ap.add_argument("--claude-dir", action="append", help="Claude Code transcript folder to use instead of the "
                    "default lookup (repeatable; for moved projects or worktrees outside the project)")
    ap.add_argument("--since", help="only sessions whose first message is on or after this date (YYYY-MM-DD)")
    ap.add_argument("--max-chars", type=int, default=6000, help="cap per message, 0 for none (default: 6000)")
    ap.add_argument("--dry-run", action="store_true", help="list what would be written")
    # agentic-loadout:begin entire-flag
    ap.add_argument("--entire", action="store_true", help="also read Entire checkpoints (git data) for sessions the agent "
                    "no longer keeps; needs a git repository, never rewrites an existing file")
    # agentic-loadout:end entire-flag
    args = ap.parse_args(argv)

    project = Path(args.project).resolve()
    in_repo, main_checkout, roots = git_layout(project)
    out = Path(args.out) if args.out else Path("memory/sessions")
    if not args.out and main_checkout:
        out = main_checkout / "memory" / "sessions"
        if not args.dry_run:
            link_archive(project / "memory" / "sessions", out)
    sessions = find_sessions(project, args.claude_dir, roots)
    # agentic-loadout:begin entire-only
    if args.entire and not sessions:
        return entire_main(project, out, args)
    # agentic-loadout:end entire-only
    if not sessions:
        print(f"no Claude Code, Codex or opencode sessions found for {project}", file=sys.stderr)
        return 1
    rendered = {}
    for client, path, reader in sessions:
        name, text = render(client, path, reader, args.max_chars)
        # A resumed or forked session can appear in two folders under one id: keep the longer copy.
        if name and not (args.since and name[:10] < args.since) and len(text) > len(rendered.get(name, ("", ""))[1]):
            rendered[name] = (client, text)
    counts = {"new": 0, "updated": 0, "unchanged": 0}
    for name, (client, text) in sorted(rendered.items()):
        target = out / name
        old = target.read_text(encoding="utf-8") if target.exists() else None
        state = "new" if old is None else "unchanged" if old == text else "updated"
        counts[state] += 1
        if state == "unchanged":
            continue
        if not args.dry_run:
            out.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            if in_repo and out.name == "sessions" and inside(out.resolve(), main_checkout or project):
                ensure_ignored(out.resolve())
        print(f"{state:8} {target}  ({client}, {len(text) // 1024} KB)")
    print(", ".join(f"{v} {k}" for k, v in counts.items()), file=sys.stderr)
    # agentic-loadout:begin entire-run
    if args.entire:
        entire_main(project, out, args, planned=set(rendered))
    # agentic-loadout:end entire-run
    return 0


if __name__ == "__main__":
    sys.exit(main())
