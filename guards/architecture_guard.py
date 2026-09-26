"""Architecture Guard — policy/immutable.md P1·P5·P6를 diff에 대해 검사한다.

veto: 병합 불가. flag: 병합은 가능하나 Chief Architect 검토 항목으로 에스컬레이션.

P6 파일 길이(ADR-2026-09-10-C D2): 500줄 flag(P6.line_warn) · 800줄 flag(P6.line_review)
· 1,000줄 veto(P6.line_cap, 파일 상단 `loc-allow: <사유>`로 예외).
"""
from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path

from common import (
    LOC_ALLOW_HEAD_LINES,
    LOC_ALLOW_MARKER,
    SRC_LINE_CAP,
    SRC_LINE_REVIEW,
    SRC_LINE_WARN,
    Finding,
    Report,
    added_lines,
    changed_files,
    diff_of,
    file_at,
    removed_lines,
)

FROZEN = ("aios/kernel/policy/**", "aios/kernel/permission/**")
FROZEN_PAPER_ONLY = (
    "src/core/strategy/**",
    "src/core/portfolio/**",
    "src/core/risk/**",
    "src/core/executor/**",
)
CONTRACT_GLOBS = ("src/foundation/*/contracts/v1.py", "src/contracts/*.py", "src/api/schemas/*.py")
META_CONTROL = (".aios-zone", "CODEOWNERS", ".github/workflows/*", "scripts/check_zone_manifest.py")
_FIELD_RE = re.compile(r"^\s{4}([a-z_][a-z0-9_]*)\s*:\s*(.+?)(\s*=.*)?$")


def _has_loc_allow(text: str) -> bool:
    head = text.splitlines()[:LOC_ALLOW_HEAD_LINES]
    return any(LOC_ALLOW_MARKER in line and line.lstrip().startswith("#") for line in head)


def _line_length_findings(path: str, text: str, n: int) -> list[Finding]:
    """P6 (ADR-2026-09-10-C D2): 1,000줄 veto(loc-allow 예외), 800줄·500줄 flag."""
    if n > SRC_LINE_CAP and not _has_loc_allow(text):
        return [Finding("architecture", "P6.line_cap", "veto", path,
                        f"{n}줄 > {SRC_LINE_CAP} (예외: 첫 {LOC_ALLOW_HEAD_LINES}줄 내 `# loc-allow: <사유>`)")]
    if n > SRC_LINE_REVIEW:
        return [Finding("architecture", "P6.line_review", "flag", path,
                        f"{n}줄 > {SRC_LINE_REVIEW} — 아키텍처 리뷰(책임 둘 이상? 독립 변경축? 공개/비공개 분리?)")]
    if n > SRC_LINE_WARN:
        return [Finding("architecture", "P6.line_warn", "flag", path,
                        f"{n}줄 > {SRC_LINE_WARN} — 리뷰어가 책임 혼합 확인")]
    return []


def _match(path: str, globs: tuple[str, ...]) -> bool:
    for g in globs:
        if g.endswith("/**"):
            if path.startswith(g[:-3] + "/"):
                return True
        elif fnmatch.fnmatch(path, g):
            return True
    return False


def _contract_fields(text: str | None) -> dict[str, tuple[str, bool]]:
    """{"Class.field": (type, required)} — AST로 클래스 본문의 주석 대입(AnnAssign)만 읽는다.

    2026-09-08(esc-2035): 이전 구현은 '4칸 들여쓰기 name: type' 정규식으로 필드를 모아 파일 단위
    평면 dict에 담았다. 계약 파일에 여러 줄 함수 시그니처가 들어가면 그 인자(outcome/reason_codes 등)가
    같은 이름의 pydantic 필드를 덮어써 P5.contract_type_changed 오탐 veto가 났고 워커 한 턴을 버렸다.
    AST는 함수 인자·dict 리터럴·다중행 호출을 필드로 오인하지 않고, 키를 클래스로 한정해 동명 필드 충돌도 없앤다.
    타입 문자열은 ast.unparse로 정규화되므로 before/after가 같은 규칙으로 비교된다.
    """
    fields: dict[str, tuple[str, bool]] = {}
    if not text:
        return fields
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return fields
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
                continue
            name = stmt.target.id
            if name.startswith("model_") or name.startswith("_"):
                continue
            typ = ast.unparse(stmt.annotation)
            fields[f"{node.name}.{name}"] = (typ, stmt.value is None)
    return fields


def check(repo: Path, base: str, head: str, *, frozen_approved: bool) -> Report:
    rep = Report(base=base, head=head)
    for status, path in changed_files(repo, base, head):
        if _match(path, FROZEN):
            rep.findings.append(Finding("architecture", "P1.frozen", "veto", path, "FROZEN 경로 변경"))
        if _match(path, FROZEN_PAPER_ONLY) and not frozen_approved:
            rep.findings.append(
                Finding("architecture", "P1.frozen_paper_only", "veto", path,
                        "FROZEN_PAPER_ONLY 변경인데 task decision에 'FROZEN 승인' 없음")
            )
        if _match(path, META_CONTROL):
            rep.findings.append(
                Finding("architecture", "P8.meta_control", "flag", path,
                        "통제면 파일 변경 — Chief Architect 검토")
            )
        if path.startswith("src/") and path.endswith(".py") and status != "D":
            text = file_at(repo, head, path) or ""
            n = text.count("\n") + 1
            rep.findings.extend(_line_length_findings(path, text, n))
        if _match(path, CONTRACT_GLOBS) and status == "M":
            before = _contract_fields(file_at(repo, base, path))
            after = _contract_fields(file_at(repo, head, path))
            for name, (typ, required) in before.items():
                if name not in after:
                    rep.findings.append(
                        Finding("architecture", "P5.contract_field_removed", "veto", path,
                                f"필드 삭제: {name}")
                    )
                elif after[name][0] != typ:
                    rep.findings.append(
                        Finding("architecture", "P5.contract_type_changed", "veto", path,
                                f"타입 변경: {name}: {typ} → {after[name][0]}")
                    )
                elif after[name][1] and not required:
                    rep.findings.append(
                        Finding("architecture", "P5.contract_required", "veto", path,
                                f"옵션→필수: {name}")
                    )
        if path.startswith("src/db/migrations/versions/") and status == "A":
            text = file_at(repo, head, path) or ""
            if "down_revision" not in text:
                rep.findings.append(Finding("architecture", "P6.migration", "veto", path, "down_revision 없음"))
        d = diff_of(repo, base, head, path)
        if any("UPDATE " in ln and " SET " in ln for ln in added_lines(d)) and path.startswith("src/"):
            joined = "\n".join(added_lines(d))
            if "WHERE" in joined and not re.search(r"WHERE[^;]*(status|state|version|fence|expected|IS NULL|>=|<)", joined):
                rep.findings.append(
                    Finding("architecture", "P7.unconditional_update", "flag", path,
                            "조건 없는 UPDATE로 보임 — 105번 표준 검토")
                )
        _ = removed_lines  # (security_guard에서 사용)
    return rep
