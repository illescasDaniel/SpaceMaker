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
#   ./copy-venv.sh --force   # always replace .venv/node_modules
#
# Without --force an existing .venv is kept only if spacemaker imports from this
# worktree's src/ and pytest runs; a valid one is skipped, a broken one is
# replaced. An existing node_modules is kept if @biomejs/biome is present.
# Works from inside any worktree (e.g. one the Claude desktop app created).

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

# `git worktree list` always prints the main (primary) working tree first,
# regardless of where the other worktrees live (~/.cursor/worktrees/,
# <primary>/.claude/worktrees/, sibling dirs, ...).
primary_root=""
while IFS= read -r line; do
	[[ -z "${line}" ]] && continue
	primary_root="${line%%[[:space:]]*}"
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
	dst_pytest="${dest_root}/.venv/Scripts/pytest.exe"
else
	dst_python="${dest_root}/.venv/bin/python"
	dst_pytest="${dest_root}/.venv/bin/pytest"
fi

# ---------------------------------------------------------------------------
# 3. .venv: copy + rewrite, or regenerate
# ---------------------------------------------------------------------------
src_venv="${primary_root}/.venv"
dst_venv="${dest_root}/.venv"

# An existing .venv (e.g. created by the Claude desktop app when it made this
# worktree) is only reused if it really works for *this* worktree.
venv_is_valid() {
	local file
	[[ -x "${dst_python}" ]] || return 1
	file="$("${dst_python}" -c "import spacemaker; print(spacemaker.__file__)" 2>/dev/null)" || return 1
	file="${file//\\//}"
	[[ "${file}" == "${dest_root}/src/"* ]] || return 1
	# Run the console script itself: it carries the shebang that must be rewritten.
	"${dst_pytest}" --version >/dev/null 2>&1
}

skip_venv=false
if [[ -e "${dst_venv}" || -L "${dst_venv}" ]]; then
	if [[ "${FORCE}" == true ]]; then
		echo "copy-venv: removing existing destination .venv (--force)..."
		rm -rf "${dst_venv}"
	elif venv_is_valid; then
		echo "copy-venv: existing .venv is valid for this worktree; skipping (use --force to replace)."
		skip_venv=true
	else
		echo "copy-venv: existing .venv is broken or points at another checkout; replacing it..."
		rm -rf "${dst_venv}"
	fi
fi

if [[ "${skip_venv}" == true ]]; then
	:
elif [[ -d "${src_venv}" ]]; then
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

skip_node_modules=false
if [[ -e "${dst_node_modules}" || -L "${dst_node_modules}" ]]; then
	if [[ "${FORCE}" == true ]]; then
		echo "copy-venv: removing existing destination node_modules (--force)..."
		rm -rf "${dst_node_modules}"
	elif [[ -d "${dst_node_modules}/@biomejs/biome" ]]; then
		echo "copy-venv: existing node_modules looks complete; skipping (use --force to replace)."
		skip_node_modules=true
	else
		echo "copy-venv: existing node_modules is incomplete; replacing it..."
		rm -rf "${dst_node_modules}"
	fi
fi

if [[ "${skip_node_modules}" == true ]]; then
	:
elif [[ -d "${src_node_modules}" ]]; then
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

pytest_probe="$("${dst_pytest}" --version 2>&1)" || {
	echo "error: pytest from destination venv failed: ${pytest_probe}" >&2
	exit 1
}
echo "  pytest: ${pytest_probe}"
echo "  node_modules/@biomejs/biome: present"

echo ""
echo "copy-venv: done."
echo "  source : ${primary_root}"
echo "  dest   : ${dest_root}"
