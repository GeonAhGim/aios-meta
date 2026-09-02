"""Guard 실행기 — Orchestrator와 CI가 같은 진입점을 쓴다.

사용:
  python C:\\aios\\meta\\guards\\run_guards.py --repo C:\\aios\\wt\\backend-1 --base origin/main --head HEAD [--frozen-approved] [--json out.json]

종료코드: 0 통과(flag 있어도 0, JSON에 flagged=true), 2 veto.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import architecture_guard
import security_guard
from common import Report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--frozen-approved", action="store_true")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    repo = Path(a.repo)

    arch = architecture_guard.check(repo, a.base, a.head, frozen_approved=a.frozen_approved)
    sec = security_guard.check(repo, a.base, a.head)
    merged = Report(base=a.base, head=a.head, findings=arch.findings + sec.findings)
    out = merged.to_json()
    if a.json:
        Path(a.json).write_text(out, encoding="utf-8")
    print(out)
    return 2 if merged.vetoed else 0


if __name__ == "__main__":
    sys.exit(main())
