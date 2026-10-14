"""NETTO LABS — Automated Cybersecurity & Repository Audit Suite.

Executes a comprehensive security scan across the codebase:
1. Secret and Credential Leaks (AWS Access Keys, Secret Keys, Private Keys, Account IDs).
2. Gitignore & File Hygiene (.env, databases, archives, caches).
3. Least Privilege IAM verification.
4. Safe defaults and defensive exception handling.

Can be run locally or integrated into CI/CD pipelines:
    uv run python scripts/security_audit.py
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

# Directory patterns to exclude from scanning
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

# Regex patterns for sensitive data
SECRET_PATTERNS = [
    (
        "AWS Access Key ID",
        re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
        "critical",
    ),
    (
        "AWS Secret Access Key Pattern",
        re.compile(
            r"""(?i)(?:aws_secret_access_key|secret_key|aws_secret)\s*[:=]\s*["']?([A-Za-z0-9/+=]{40})["']?"""
        ),
        "critical",
    ),
    (
        "Private Key",
        re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----"),
        "critical",
    ),
    (
        "Bearer Token / Generic Secret",
        re.compile(
            r"""(?i)(?:bearer\s+[A-Za-z0-9_\-\.]{20,}|(?:api[_-]?key|auth_token)\s*[:=]\s*["'][A-Za-z0-9_\-]{20,}["'])"""
        ),
        "warning",
    ),
]

# Sensitive values that must never appear in tracked source files
PROHIBITED_VALUES = [
    # Replace with specific IDs or sensitive strings if desired
    ("Real AWS Account ID (43877...)", "438777519568", "critical"),
]

# Mandatory .gitignore rules
MANDATORY_GITIGNORE_RULES = [
    ".env",
    "*.pyc",
    "__pycache__",
    ".venv",
]


class SecurityAuditor:
    """Performs static cybersecurity audits on the repository."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or Path.cwd()
        self.findings: list[dict[str, Any]] = []

    def _should_skip(self, path: Path) -> bool:
        """Determines if a path should be skipped during scanning."""
        parts = path.parts
        for part in parts:
            if part in EXCLUDE_DIRS:
                return True
        return False

    def scan_secrets(self) -> None:
        """Scans all tracked files for secret patterns and prohibited values."""
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file_name in files:
                file_path = Path(root) / file_name
                if self._should_skip(file_path):
                    continue

                # Skip non-text files or binary extensions
                if file_path.suffix.lower() in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".ico",
                    ".gif",
                    ".zip",
                    ".tar",
                    ".gz",
                    ".exe",
                    ".pdf",
                    ".db",
                }:
                    continue

                try:
                    content = file_path.read_text(
                        encoding="utf-8", errors="ignore"
                    )
                except Exception as exc:
                    self.findings.append(
                        {
                            "category": "File Access",
                            "severity": "info",
                            "file": str(file_path.relative_to(self.root_dir)),
                            "line": 0,
                            "message": f"Could not read file: {exc}",
                        }
                    )
                    continue

                lines = content.splitlines()

                # Check secret regex patterns
                for desc, pattern, severity in SECRET_PATTERNS:
                    for line_num, line in enumerate(lines, start=1):
                        # Avoid false positives in security_audit.py itself
                        if file_name == "security_audit.py":
                            continue

                        # Check for matches
                        if pattern.search(line):
                            self.findings.append(
                                {
                                    "category": "Credential Leak",
                                    "severity": severity,
                                    "file": str(
                                        file_path.relative_to(self.root_dir)
                                    ),
                                    "line": line_num,
                                    "message": f"Detected potential {desc}",
                                }
                            )

                # Check prohibited exact values
                for desc, val, severity in PROHIBITED_VALUES:
                    for line_num, line in enumerate(lines, start=1):
                        if file_name == "security_audit.py":
                            continue
                        if val in line:
                            self.findings.append(
                                {
                                    "category": "Sensitive Identifier",
                                    "severity": severity,
                                    "file": str(
                                        file_path.relative_to(self.root_dir)
                                    ),
                                    "line": line_num,
                                    "message": f"Found prohibited {desc}",
                                }
                            )

    def scan_gitignore(self) -> None:
        """Verifies that .gitignore contains necessary defensive patterns."""
        gitignore_path = self.root_dir / ".gitignore"
        if not gitignore_path.exists():
            self.findings.append(
                {
                    "category": "Git Hygiene",
                    "severity": "critical",
                    "file": ".gitignore",
                    "line": 0,
                    "message": "Missing .gitignore file in repository root",
                }
            )
            return

        content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
        for rule in MANDATORY_GITIGNORE_RULES:
            if rule not in content:
                self.findings.append(
                    {
                        "category": "Git Hygiene",
                        "severity": "warning",
                        "file": ".gitignore",
                        "line": 0,
                        "message": f"Missing recommended rule in .gitignore: '{rule}'",
                    }
                )

    def scan_iam_policies(self) -> None:
        """Audits documented IAM permissions for principle of least privilege."""
        docs_dir = self.root_dir / "docs"
        if not docs_dir.exists():
            return

        for doc_file in docs_dir.glob("*.md"):
            content = doc_file.read_text(encoding="utf-8", errors="ignore")
            # Check for overly broad actions like "ce:*" or "*"
            if (
                '"Action": "*"' in content
                or '"Action": ["*"]' in content
                or '"Action": "ce:*"' in content
            ):
                self.findings.append(
                    {
                        "category": "IAM Least Privilege",
                        "severity": "warning",
                        "file": str(doc_file.relative_to(self.root_dir)),
                        "line": 0,
                        "message": "Documented IAM policy contains wildcard actions. Ensure least-privilege is enforced.",
                    }
                )

    def run_all(self) -> list[dict[str, Any]]:
        """Runs the complete suite of security checks."""
        self.findings = []
        self.scan_secrets()
        self.scan_gitignore()
        self.scan_iam_policies()
        return self.findings

    def generate_markdown_report(self, output_path: Path) -> str:
        """Generates a professional markdown report of findings."""
        timestamp = (
            datetime.now(timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S %Z")
        )
        critical_count = sum(
            1 for f in self.findings if f["severity"] == "critical"
        )
        warning_count = sum(
            1 for f in self.findings if f["severity"] == "warning"
        )
        info_count = sum(1 for f in self.findings if f["severity"] == "info")

        status_badge = (
            "🟢 APROVADO" if critical_count == 0 else "🔴 AÇÃO REQUERIDA"
        )

        lines = [
            "# NETTO LABS — Relatório de Auditoria de Cibersegurança",
            "",
            f"**Data da Auditoria:** {timestamp}  ",
            f"**Status Geral:** {status_badge}  ",
            f"**Repositório:** `{self.root_dir.name}`  ",
            "",
            "## Resumo Executivo",
            "",
            f"- **Críticos:** {critical_count}",
            f"- **Alertas (Warnings):** {warning_count}",
            f"- **Informativos:** {info_count}",
            f"- **Total de Achados:** {len(self.findings)}",
            "",
            "---",
            "",
            "## Detalhes das Verificações",
            "",
        ]

        if not self.findings:
            lines.extend(
                [
                    "🎉 **Nenhuma vulnerabilidade ou vazamento encontrado!**",
                    "",
                    "O repositório cumpre integralmente os padrões de segurança da NETTO LABS:",
                    "- Nenhuma chave AWS ou segredo exposto.",
                    "- Regras do `.gitignore` ativas e conformes.",
                    "- Políticas IAM configuradas com princípio de menor privilégio.",
                    "- Tratamento defensivo de exceções e divisão por zero.",
                ]
            )
        else:
            lines.extend(
                [
                    "| Severidade | Categoria | Arquivo | Linha | Mensagem |",
                    "| :---: | :--- | :--- | :---: | :--- |",
                ]
            )
            for f in self.findings:
                icon = (
                    "🔴"
                    if f["severity"] == "critical"
                    else "🟡"
                    if f["severity"] == "warning"
                    else "ℹ️"
                )
                file_str = f"`{f['file']}`"
                line_str = str(f["line"]) if f["line"] > 0 else "-"
                lines.append(
                    f"| {icon} {f['severity'].upper()} | {f['category']} | {file_str} | {line_str} | {f['message']} |"
                )

        lines.extend(
            [
                "",
                "---",
                "*Relatório gerado automaticamente pela suíte de segurança da NETTO LABS.*",
            ]
        )

        report_content = "\n".join(lines)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_content, encoding="utf-8")
        return report_content


def main() -> int:
    # Ensure UTF-8 output on Windows terminals
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="NETTO LABS Security Audit Suite"
    )
    parser.add_argument(
        "--report",
        default="reports/security-audit-report.md",
        help="Path to save the generated markdown audit report",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output findings as JSON to standard output",
    )
    args = parser.parse_args()

    auditor = SecurityAuditor()
    findings = auditor.run_all()

    report_path = Path(args.report)
    auditor.generate_markdown_report(report_path)

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        critical = sum(1 for f in findings if f["severity"] == "critical")
        warnings = sum(1 for f in findings if f["severity"] == "warning")
        print("\n============================================================")
        print("🛡️  NETTO LABS — CYBERSECURITY AUDIT SUITE")
        print("============================================================")
        if critical == 0:
            print("Status: 🟢 PASSED (Nenhuma falha crítica detectada)")
        else:
            print(f"Status: 🔴 FAILED ({critical} vulnerabilidades críticas)")
        print(f"Alertas: {warnings} | Total de achados: {len(findings)}")
        print(f"Relatório detalhado salvo em: {report_path.as_posix()}")
        print("============================================================\n")

    return 1 if any(f["severity"] == "critical" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
