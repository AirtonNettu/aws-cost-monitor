"""Unit tests for the NETTO LABS Security Audit Suite."""

from pathlib import Path
import tempfile
from scripts.security_audit import SecurityAuditor


def test_clean_repo_passes():
    """Tests that a clean repository without leaks returns no critical findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create minimal valid structure
        (root / ".gitignore").write_text(
            ".env\n*.pyc\n__pycache__\n.venv\n", encoding="utf-8"
        )
        (root / "main.py").write_text("print('hello')", encoding="utf-8")

        auditor = SecurityAuditor(root_dir=root)
        findings = auditor.run_all()
        critical = [f for f in findings if f["severity"] == "critical"]
        assert len(critical) == 0


def test_catches_aws_access_key():
    """Tests that the auditor detects an AWS Access Key pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".gitignore").write_text(
            ".env\n*.pyc\n__pycache__\n.venv\n", encoding="utf-8"
        )
        # Construct fake key dynamically to avoid tripping scanner
        fake_key = "AKIA" + "IOSFODNN7EXAMPLE"
        (root / "leaky_file.py").write_text(
            f"AWS_KEY = '{fake_key}'", encoding="utf-8"
        )

        auditor = SecurityAuditor(root_dir=root)
        findings = auditor.run_all()
        critical = [f for f in findings if f["severity"] == "critical"]
        assert len(critical) > 0
        assert any("AWS Access Key ID" in f["message"] for f in critical)


def test_catches_missing_gitignore():
    """Tests that a missing .gitignore produces a critical finding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        auditor = SecurityAuditor(root_dir=root)
        findings = auditor.run_all()
        critical = [f for f in findings if f["severity"] == "critical"]
        assert len(critical) > 0
        assert any(".gitignore" in f["message"] for f in critical)


def test_markdown_report_generation():
    """Tests that the markdown report is properly formatted and saved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".gitignore").write_text(
            ".env\n*.pyc\n__pycache__\n.venv\n", encoding="utf-8"
        )
        report_file = root / "reports" / "audit.md"

        auditor = SecurityAuditor(root_dir=root)
        auditor.run_all()
        report_content = auditor.generate_markdown_report(report_file)

        assert report_file.exists()
        assert "NETTO LABS" in report_content
        assert "APROVADO" in report_content
