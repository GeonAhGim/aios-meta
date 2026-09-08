# Meta-Control Plane 보호 설정 — 사람이 세션 밖에서 수행

이 저장소(`C:\aios\meta`)는 에이전트가 쓸 수 없어야 한다. 아래는 사람만 할 수 있는 단계다.
완료 전까지 Guard는 Orchestrator에서만 실행되고(에이전트 프로세스 내부 — 약한 보장),
완료 후에는 CI에서도 실행돼 에이전트가 우회할 수 없다(강한 보장).

## 1. GitHub 저장소 생성 (public — 정책·Guard 코드뿐이라 비밀이 없고, 무료 플랜에서 브랜치 보호가 켜진다)
```
cd C:\aios\meta
git add -A && git commit -m "meta: immutable policy + guards v1"
gh repo create GeonAhGim/aios-meta --public --source . --push
```

## 2. 브랜치 보호 (GitHub 웹 → Settings → Branches → main)
- Require a pull request before merging, Require review from Code Owners, Do not allow bypassing.
- `CODEOWNERS`(이 저장소 루트)에 `* @GeonAhGim` — 사람 계정만.
- 현재 에이전트가 사용자 계정(gh 로그인)으로 동작하므로 계정 분리는 불가능하다. 대신 `enforce_admins`
  + CODEOWNERS 리뷰 필수로 **PR 작성자(에이전트=같은 계정)가 자기 PR을 승인할 수 없게** 한다 — 사람이
  GitHub 웹에서 직접 승인·병합할 때만 변경된다. 직접 push는 관리자에게도 막힌다.

## 3. mihwa-aios CI에 Guard 연결
- public 저장소라 토큰이 필요 없다. `.github/workflows/quality.yml`의 `guards` job이 aios-meta를
  **고정 커밋**(`META_GUARDS_REF` repository variable)으로 checkout해 `guards/run_guards.py`를 실행한다.
- `META_GUARDS_REF`가 없으면 job은 실패한다(건너뛰지 않음). SHA를 올리는 것도 사람이 한다
  (`gh variable set META_GUARDS_REF --repo GeonAhGim/mihwa-aios --body <sha>`).

## 4. 로컬 보호(선택)
- `C:\aios\meta`를 읽기 전용 속성으로 두고, 에이전트 실행 계정과 분리하려면 별도 Windows 사용자로
  체크아웃한다. 최소한 `git remote`를 read-only URL로 둔다.

## 5. 변경 절차
- 정책·Guard 변경 = 이 저장소에 PR → 사람 리뷰 → 병합 → `META_GUARDS_REF` 갱신.
- Chief Architect(Fable)는 변경 **제안서**를 `C:\aios\pm\escalations\`에 남길 뿐, 직접 수정하지 않는다.

## 2026-09-08 위임 기록 — Chief Architect 머지 권한

사용자가 aios-meta에 대해서도 Chief Architect(에이전트)에게 전권을 승인했다("aios-meta도 너에게 전권을 승인한다").
본인 PR은 본인이 승인할 수 없어 `required_pull_request_reviews`(승인 1건 + 코드오너)를 해제했다.
유지되는 것: `enforce_admins`, force-push·삭제 금지. 변경 절차는 그대로 **브랜치 + PR**이며 머지만 에이전트가 한다.
가드 규칙을 **약화**하는 변경은 이 위임 범위 밖으로 보고 사람 확인을 받는다(파서 버그 수정처럼 정확도를 높이는 것만 자체 머지).
첫 적용: PR #1(architecture_guard 계약 파서 정규식→AST, esc-2035). ADR-2026-09-08-A D8.
