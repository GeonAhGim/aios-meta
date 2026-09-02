"""Security Guard — policy/immutable.md P2·P3·P4를 diff에 대해 검사한다.

veto: 병합 불가. flag: Chief Architect(보안) 검토.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    Finding,
    Report,
    added_lines,
    changed_files,
    diff_of,
    file_at,
    removed_lines,
)

LIVE_GUARD_FILE = "src/core/executor/executor.py"
LIVE_GUARD_MARKERS = ('mode != "PAPER"', "is_paper_trading", "is_sandboxed")
FUND_MOVING_METHODS = re.compile(
    r"async def (place_order|cancel_order|modify_order|transfer|borrow|repay|execute_convert|"
    r"place_spot_grid|place_futures_grid|subscribe_earn|redeem|withdraw)\b"
)
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|passphrase|token|password)\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{16,}['\"]"),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
    re.compile(r"(?i)^\s*(BITGET|KIS|NH|JWT|CREDENTIAL)_[A-Z_]*(KEY|SECRET)\s*=\s*\S{8,}", re.MULTILINE),
]
WORM_RE = re.compile(r"REVOKE\s+(UPDATE|DELETE|UPDATE,\s*DELETE)", re.IGNORECASE)
LEDGER_TABLES = ("audit_log", "wallet_transactions", "audit_event", "ledger_entry", "pos_journal")


def check(repo: Path, base: str, head: str) -> Report:
    rep = Report(base=base, head=head)
    for status, path in changed_files(repo, base, head):
        d = diff_of(repo, base, head, path)
        removed = removed_lines(d)
        added = added_lines(d)

        # P4 시크릿
        if path.endswith(".env") or path.split("/")[-1] == ".env":
            rep.findings.append(Finding("security", "P4.env_committed", "veto", path, ".env 커밋"))
        for ln in added:
            for pat in SECRET_PATTERNS:
                if pat.search(ln) and "example" not in path and "test" not in path:
                    rep.findings.append(Finding("security", "P4.secret_literal", "veto", path, ln.strip()[:80]))
                    break

        # P2 LIVE 하드가드
        if path == LIVE_GUARD_FILE:
            text = file_at(repo, head, path) or ""
            for marker in LIVE_GUARD_MARKERS:
                if marker not in text:
                    rep.findings.append(
                        Finding("security", "P2.live_guard_removed", "veto", path, f"가드 마커 없음: {marker}")
                    )
            if any("PAPER" in ln for ln in removed):
                rep.findings.append(Finding("security", "P2.live_guard_touched", "flag", path, "PAPER 가드 줄 변경"))
        if path.startswith("src/exchanges/") and status != "D":
            text = file_at(repo, head, path) or ""
            for m in FUND_MOVING_METHODS.finditer(text):
                start = max(0, m.start() - 200)
                if "require_paper_sandbox" not in text[start:m.start()] and "common/adapter.py" not in path and "/nh/" not in path:
                    rep.findings.append(
                        Finding("security", "P2.fund_method_unguarded", "flag", path,
                                f"{m.group(1)}에 @require_paper_sandbox 없음")
                    )
            if any("is_sandboxed" in ln and "True" in ln for ln in added):
                rep.findings.append(
                    Finding("security", "P2.sandbox_claim", "flag", path, "is_sandboxed=True 추가 — 공식 문서 근거 확인")
                )

        # P3 WORM
        if path.startswith("src/db/migrations/"):
            if any(WORM_RE.search(ln) for ln in removed):
                rep.findings.append(Finding("security", "P3.worm_removed", "veto", path, "REVOKE 제거"))
            joined = "\n".join(added)
            if re.search(r"GRANT\s+(UPDATE|DELETE)", joined, re.IGNORECASE) and any(t in joined for t in LEDGER_TABLES):
                rep.findings.append(Finding("security", "P3.worm_grant", "veto", path, "원장 테이블에 UPDATE/DELETE GRANT"))
            if re.search(r"DROP\s+TABLE\s+(audit_log|wallet_transactions|audit_event)", joined, re.IGNORECASE) and "def downgrade" not in joined:
                rep.findings.append(Finding("security", "P3.ledger_drop", "veto", path, "원장 테이블 DROP"))

        # P4 시크릿 경계 우회
        if path.startswith("src/") and any(".get_secret_value()" in ln and ("log" in ln or "print(" in ln) for ln in added):
            rep.findings.append(Finding("security", "P4.secret_logged", "veto", path, "시크릿 값 로그/출력"))
        if path.startswith("src/") and any(re.search(r"(?i)verify\s*=\s*False", ln) for ln in added):
            rep.findings.append(Finding("security", "P4.tls_verify_off", "veto", path, "TLS 검증 비활성화"))
    return rep
