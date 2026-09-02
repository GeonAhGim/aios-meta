"""Guard 공용 — 변경 파일 목록·diff·JSON 리포트. 에이전트가 수정할 수 없는 저장소(aios-meta)에 산다."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

SRC_LINE_CAP = 300


@dataclass
class Finding:
    guard: str
    rule: str
    severity: str  # "veto" | "flag"
    file: str
    message: str


@dataclass
class Report:
    base: str
    head: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def vetoed(self) -> bool:
        return any(f.severity == "veto" for f in self.findings)

    @property
    def flagged(self) -> bool:
        return any(f.severity == "flag" for f in self.findings)

    def to_json(self) -> str:
        return json.dumps(
            {
                "base": self.base,
                "head": self.head,
                "vetoed": self.vetoed,
                "flagged": self.flagged,
                "findings": [f.__dict__ for f in self.findings],
            },
            ensure_ascii=False,
            indent=2,
        )


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def changed_files(repo: Path, base: str, head: str) -> list[tuple[str, str]]:
    """[(status, path)] — status: A/M/D/R."""
    out = git(repo, "diff", "--name-status", f"{base}..{head}")
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            rows.append((parts[0][0], parts[-1]))
    return rows


def file_at(repo: Path, rev: str, path: str) -> str | None:
    try:
        return git(repo, "show", f"{rev}:{path}")
    except RuntimeError:
        return None


def diff_of(repo: Path, base: str, head: str, path: str) -> str:
    try:
        return git(repo, "diff", f"{base}..{head}", "--", path)
    except RuntimeError:
        return ""


def removed_lines(diff_text: str) -> list[str]:
    return [ln[1:] for ln in diff_text.splitlines() if ln.startswith("-") and not ln.startswith("---")]


def added_lines(diff_text: str) -> list[str]:
    return [ln[1:] for ln in diff_text.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
