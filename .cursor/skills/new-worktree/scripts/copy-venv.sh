#!/usr/bin/env bash
# Copy .venv and node_modules from the primary SpaceMaker checkout into the
# current worktree so `uv run task checks` works immediately, with no
# re-downloads.
#
# Mirrors .venv (robocopy on Windows, rsync elsewhere) from the primary
# checkout -- the git worktree list entry that is under neither
# ~/.cursor/worktrees/ nor <repo>/.claude/worktrees/ -- rewrites shebangs /
# editable .pth files / direct_url.json for every uv workspace member
# (spacemaker, codenav-mcp, webnav-mcp, mcp-nav-shared), then runs a cheap
# offline `uv sync --group dev` to confirm the editable installs are
# registered. Mirrors node_modules the same way (no path rewrite needed --
# SpaceMaker's devDependencies are all registry packages, so the npm-generated
# .bin/*.cmd shims carry no absolute paths).
#
# If a source .venv/node_modules doesn't exist (or was never synced), falls
# back to regenerating instead of copying: `uv sync --group dev` / `npm ci`.
#
# Usage:
#   ./copy-venv.sh           # from the worktree root (or via the /new-worktree skill)
#   ./copy-venv.sh --force   # overwrite an existing destination .venv/node_modules

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FORCE=false
for arg in "$@"; do
	case "${arg}" in
	--force | -f)
		FORCE=true
		;;
	-h | --help)
		cat <<'EOF'
Usage: copy-venv.sh [--force|-f]

Copy .venv and node_modules from the primary SpaceMaker checkout into this
worktree, rewrite .venv's shebangs/editable paths, then run
`uv sync --group dev` and verify node_modules/@biomejs/biome exists.
EOF
		exit 0
		;;
	*)
		echo "error: unknown argument: ${arg}" >&2
		echo "Usage: copy-venv.sh [--force|-f]" >&2
		exit 1
		;;
	esac
done

case "$(uname -s)" in
MINGW* | MSYS* | CYGWIN*) IS_WINDOWS=true ;;
*) IS_WINDOWS=false ;;
esac

# ---------------------------------------------------------------------------
# 1. Resolve current worktree root
# ---------------------------------------------------------------------------
if ! dest_root="$(git rev-parse --show-toplevel 2>&1)"; then
	echo "error: Not inside a git repository. Run this from within a SpaceMaker worktree." >&2
	exit 1
fi

# ---------------------------------------------------------------------------
# 2. Parse git worktree list to find the primary checkout
# ---------------------------------------------------------------------------
if ! worktree_list="$(git worktree list 2>&1)"; then
	echo "error: git worktree list failed: ${worktree_list}" >&2
	exit 1
fi

cursor_worktrees="${HOME}/.cursor/worktrees"
primary_root=""
while IFS= read -r line; do
	[[ -z "${line}" ]] && continue
	candidate="${line%%[[:space:]]*}"
	[[ -z "${candidate}" ]] && continue
	# The primary checkout is never under ~/.cursor/worktrees/ (Cursor) or
	# <repo>/.claude/worktrees/ (Claude Code's EnterWorktree).
	case "${candidate}/" in
	"${cursor_worktrees}"/*) continue ;;
	*/.claude/worktrees/*) continue ;;
	esac
	primary_root="${candidate}"
	break
done <<<"${worktree_list}"

if [[ -z "${primary_root}" ]]; then
	echo "error: Could not find the primary checkout in 'git worktree list'. Output was:" >&2
	echo "${worktree_list}" >&2
	exit 1
fi

dest_cmp="${dest_root%/}"
primary_cmp="${primary_root%/}"
if [[ "${dest_cmp}" == "${primary_cmp}" ]]; then
	echo "Already in the primary checkout (${primary_root}). Nothing to copy."
	exit 0
fi

if [[ "${IS_WINDOWS}" == true ]]; then
	dst_python="${dest_root}/.venv/Scripts/python.exe"
else
	dst_python="${dest_root}/.venv/bin/python"
fi

# ---------------------------------------------------------------------------
# 3. .venv: copy + rewrite, or regenerate
# ---------------------------------------------------------------------------
src_venv="${primary_root}/.venv"
dst_venv="${dest_root}/.venv"

if [[ -e "${dst_venv}" && "${FORCE}" != true ]]; then
	echo "warning: Destination .venv already exists at: ${dst_venv}" >&2
	echo "Pass --force to overwrite it, or delete it manually and re-run." >&2
	exit 1
fi
if [[ -e "${dst_venv}" && "${FORCE}" == true ]]; then
	echo "copy-venv: removing existing destination .venv (--force)..."
	rm -rf "${dst_venv}"
fi

if [[ -d "${src_venv}" ]]; then
	echo ""
	echo "copy-venv: copying .venv"
	echo "  from : ${src_venv}"
	echo "  to   : ${dst_venv}"
	echo ""
	if [[ "${IS_WINDOWS}" == true ]]; then
		mkdir -p "${dst_venv}"
		# robocopy exit codes 0-7 are success (0=no change, 1=copied, etc.).
		# MSYS_NO_PATHCONV stops Git Bash from mangling /E /NP ... into drive-letter paths (e.g. /E -> E:/).
		MSYS_NO_PATHCONV=1 robocopy "$(cygpath -w "${src_venv}")" "$(cygpath -w "${dst_venv}")" /E /NP /NFL /NDL /NJH /NJS || {
			robocopy_exit=$?
			if ((robocopy_exit >= 8)); then
				echo "error: robocopy failed with exit code ${robocopy_exit}" >&2
				exit 1
			fi
		}
	else
		if ! command -v rsync >/dev/null 2>&1; then
			echo "error: rsync is required but not found on PATH." >&2
			exit 1
		fi
		mkdir -p "${dst_venv}"
		rsync -a "${src_venv}/" "${dst_venv}/"
	fi
	echo "copy-venv: .venv copy complete"

	echo ""
	echo "copy-venv: rewriting venv paths (shebangs, editable .pth, direct_url)..."
	"${dst_python}" "${SCRIPT_DIR}/rewrite_venv_paths.py" \
		--old-root "${primary_root}" \
		--new-root "${dest_root}"

	echo ""
	echo "copy-venv: running uv sync (offline, dev group)..."
	(
		cd "${dest_root}"
		if ! uv sync --group dev --offline; then
			echo "copy-venv: offline sync failed; retrying online..."
			uv sync --group dev
		fi
	)
else
	echo "warning: no source .venv at ${src_venv}; regenerating instead of copying." >&2
	(
		cd "${dest_root}"
		uv sync --group dev
	)
fi

# ---------------------------------------------------------------------------
# 4. node_modules: copy, or regenerate
# ---------------------------------------------------------------------------
src_node_modules="${primary_root}/node_modules"
dst_node_modules="${dest_root}/node_modules"

if [[ -e "${dst_node_modules}" && "${FORCE}" != true ]]; then
	echo "warning: Destination node_modules already exists at: ${dst_node_modules}" >&2
	echo "Pass --force to overwrite it, or delete it manually and re-run." >&2
	exit 1
fi
if [[ -e "${dst_node_modules}" && "${FORCE}" == true ]]; then
	echo "copy-venv: removing existing destination node_modules (--force)..."
	rm -rf "${dst_node_modules}"
fi

if [[ -d "${src_node_modules}" ]]; then
	echo ""
	echo "copy-venv: copying node_modules"
	echo "  from : ${src_node_modules}"
	echo "  to   : ${dst_node_modules}"
	echo ""
	if [[ "${IS_WINDOWS}" == true ]]; then
		mkdir -p "${dst_node_modules}"
		MSYS_NO_PATHCONV=1 robocopy "$(cygpath -w "${src_node_modules}")" "$(cygpath -w "${dst_node_modules}")" /E /NP /NFL /NDL /NJH /NJS || {
			robocopy_exit=$?
			if ((robocopy_exit >= 8)); then
				echo "error: robocopy failed with exit code ${robocopy_exit}" >&2
				exit 1
			fi
		}
	else
		mkdir -p "${dst_node_modules}"
		rsync -a "${src_node_modules}/" "${dst_node_modules}/"
	fi
	echo "copy-venv: node_modules copy complete (no path rewrite needed -- registry packages only)"
else
	echo "warning: no source node_modules at ${src_node_modules}; regenerating instead of copying." >&2
	(
		cd "${dest_root}"
		npm ci
	)
fi

if [[ ! -d "${dest_root}/node_modules/@biomejs/biome" ]]; then
	echo "error: node_modules/@biomejs/biome missing after copy/regenerate." >&2
	exit 1
fi

# ---------------------------------------------------------------------------
# 5. Verify
# ---------------------------------------------------------------------------
echo ""
echo "copy-venv: verifying paths..."
spacemaker_file="$("${dst_python}" -c "import spacemaker; print(spacemaker.__file__)" 2>&1)" || {
	echo "error: failed to import spacemaker from destination venv: ${spacemaker_file}" >&2
	exit 1
}
# Python's __file__ uses native (backslash) separators on Windows; dest_root
# (from `git rev-parse --show-toplevel`) is always forward-slash. Normalize
# both before comparing.
spacemaker_file_unix="${spacemaker_file//\\//}"
case "${spacemaker_file_unix}" in
"${dest_root}/src/"*) echo "  spacemaker.__file__: ${spacemaker_file}" ;;
*)
	echo "error: spacemaker.__file__ is not under worktree src/: ${spacemaker_file}" >&2
	exit 1
	;;
esac

if [[ "${IS_WINDOWS}" == true ]]; then
	dst_pytest="${dest_root}/.venv/Scripts/pytest.exe"
else
	dst_pytest="${dest_root}/.venv/bin/pytest"
fi
if [[ -e "${dst_pytest}" ]]; then
	pytest_probe="$("${dst_pytest}" --version 2>&1)" || {
		echo "error: pytest from destination venv failed: ${pytest_probe}" >&2
		exit 1
	}
	echo "  pytest: ${pytest_probe}"
fi
echo "  node_modules/@biomejs/biome: present"

echo ""
echo "copy-venv: done."
echo "  source : ${primary_root}"
echo "  dest   : ${dest_root}"
