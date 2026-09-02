# Immutable Policy Layer — aios-meta

이 저장소는 **Meta-Control Plane**이다. 어떤 에이전트 세션(worker·Orchestrator·PM·Chief
Architect 포함)도 이 저장소에 쓰기 권한이 없다. 변경은 사람이 세션 밖에서만 한다
(`SETUP_PROTECTION.md`). 에이전트는 읽기 전용으로 참조하고, Guard는 CI(에이전트 통제 밖)와
Orchestrator에서 실행된다. 프롬프트 규칙이 아니라 **쓰기 권한의 물리적 부재**가 보장 수단이다.

## P1. Zone (mihwa-aios `.aios-zone`가 구현체, 이 문서가 원본 규칙)
- `FROZEN`(`aios/kernel/policy/**`, `aios/kernel/permission/**`): 어떤 PR도 불가.
- `FROZEN_PAPER_ONLY`(`src/core/strategy|portfolio|risk|executor/**`): PAPER 판단·실행 로직만.
  task `decision`에 "FROZEN 승인" 문자열이 있어야 수정 가능. LIVE 경로 개방·Executor 하드가드
  약화는 승인이 있어도 금지(P2).
- `SCAFFOLD`·`OPEN`: Guard 통과 시 병합 가능.

## P2. LIVE 하드가드 (ADR-2026-08-29-E)
- `src/core/executor/executor.py`의 `mode != "PAPER"` 차단과 `is_paper_trading`/`is_sandboxed`
  이중 검증은 삭제·우회·조건 완화 금지.
- 거래소 어댑터의 자금이동 메서드(주문·전환·대출·이체·그리드)는 `@require_paper_sandbox` 유지.
- `is_sandboxed=True`는 공식 문서로 확인된 샌드박스에만. 미확인이면 False.

## P3. 원장·감사 불변성
- `audit_log`, `wallet_transactions`, `audit_event`(foundation evidence) 및 L4 원장 명세의 저널
  테이블에 대한 `REVOKE UPDATE, DELETE`는 마이그레이션에서 제거·약화 금지.
- 환불·정산·구매 경로는 총잔액 보존(Σ=0) 테스트가 반드시 통과해야 한다.

## P4. 시크릿
- 저장소에 `.env`, API 키, 토큰, 개인키 커밋 금지. gitleaks 통과 필수.
- `SecretStr`/암호화 경계(`src/core/security`) 우회 금지. 로그·감사 데이터에 시크릿 값 기록 금지.

## P5. 계약 호환 (107번)
- `src/foundation/*/contracts/v1.py`, `src/contracts/*`, `src/api/schemas/*`의 필드 삭제·타입 변경·
  필수화는 MAJOR — `schema_version` 상향과 ADR 없이는 금지. 옵션 필드 추가만 MINOR.

## P6. 모듈 규율 (106번)
- 파일당 한 책임, 소스 파일 300줄 초과 금지(테스트 제외). 초과분은 분할.
- 마이그레이션은 단일 체인(head 하나). 다중 head 금지.

## P7. 동시성 (105번)
- 상태 전이는 조건부 UPDATE / FOR UPDATE / 멱등키. 무조건 UPDATE로 상태를 덮어쓰는 신규 코드 금지.

## P8. 거버넌스
- 리뷰 없는 직접 push는 Guard 통과 커밋에 한해 허용(현 단계). GitHub branch protection이 켜지면
  PR 필수로 전환한다.
- Guard 코드·이 정책·CI 게이트 정의의 변경은 사람만. 에이전트가 이 저장소를 수정하려는 시도는
  그 자체가 P8 위반이며 Orchestrator가 해당 task를 `blocked`로 만든다.

## P9. 스콥
- 06번 MVP + 103번 P0 우선. 거래소 API 폭 확장(02c류) 금지. NH는 PLUG OpenAPI만.
- Bitget Demo·Cursor 키 의존 작업은 키가 제공되기 전 생성 금지.
