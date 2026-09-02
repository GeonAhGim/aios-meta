# Meta-Control Plane 보호 설정 — 사람이 세션 밖에서 수행

이 저장소(`C:\aios\meta`)는 에이전트가 쓸 수 없어야 한다. 아래는 사람만 할 수 있는 단계다.
완료 전까지 Guard는 Orchestrator에서만 실행되고(에이전트 프로세스 내부 — 약한 보장),
완료 후에는 CI에서도 실행돼 에이전트가 우회할 수 없다(강한 보장).

## 1. GitHub 저장소 생성 (private)
```
cd C:\aios\meta
git add -A && git commit -m "meta: immutable policy + guards v1"
gh repo create GeonAhGim/aios-meta --private --source . --push
```

## 2. 브랜치 보호 (GitHub 웹 → Settings → Branches → main)
- Require a pull request before merging, Require review from Code Owners, Do not allow bypassing.
- `CODEOWNERS`(이 저장소 루트)에 `* @GeonAhGim` — 사람 계정만.
- 에이전트가 쓰는 자격증명(PAT/gh 로그인)에 이 저장소 **write 권한을 주지 않는다**.
  (fine-grained PAT: mihwa-aios만 contents:write, aios-meta는 read-only)

## 3. mihwa-aios CI에 Guard 연결
- mihwa-aios 저장소 Settings → Secrets → `META_REPO_TOKEN`: aios-meta **read-only** fine-grained PAT.
- `.github/workflows/quality.yml`의 `guards` job이 그 토큰으로 aios-meta를 **고정 커밋**으로 checkout해
  `guards/run_guards.py`를 실행한다. 고정 커밋 SHA는 `META_GUARDS_REF` repository variable로 관리 —
  올릴 때도 사람이 한다.
- 토큰이 없으면 job은 실패한다(건너뛰지 않음). 설정 전에는 mihwa-aios CI가 빨간 상태인 것이 의도다.

## 4. 로컬 보호(선택)
- `C:\aios\meta`를 읽기 전용 속성으로 두고, 에이전트 실행 계정과 분리하려면 별도 Windows 사용자로
  체크아웃한다. 최소한 `git remote`를 read-only URL로 둔다.

## 5. 변경 절차
- 정책·Guard 변경 = 이 저장소에 PR → 사람 리뷰 → 병합 → `META_GUARDS_REF` 갱신.
- Chief Architect(Fable)는 변경 **제안서**를 `C:\aios\pm\escalations\`에 남길 뿐, 직접 수정하지 않는다.
