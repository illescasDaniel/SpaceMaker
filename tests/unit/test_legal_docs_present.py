from pathlib import Path


_REPO = Path(__file__).resolve().parents[2]
_LEGAL = _REPO / "docs" / "legal"


def test_given_repo_when_check_legal_docs_then_required_files_exist():
	# given
	required = ("PRIVACY.md", "DISCLAIMER.md", "THIRD_PARTY_TOOLS.md", "README.md")
	# when / then
	for name in required:
		assert (_LEGAL / name).is_file(), f"missing {_LEGAL / name}"
