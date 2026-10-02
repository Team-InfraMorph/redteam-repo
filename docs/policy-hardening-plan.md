# E Policy 규칙 강화 — fixture 확장 계획

> 계획 수정: 2026-10-03. 구현·검증 완료 기록이 아님.
> 작업 브랜치: `feat/e-policy-fixtures` 유지.
> 소비 저장소: inframorph `feat/e-policy-hardening`, main 기준 `800681b`.

## 범위

원래 Policy 목표인 스키마·근거 실존/관계·공개 범위·패치 규칙을 검증한다. RAG 확장은 포함하지 않는다. 정책 상세 UI와 Gate 구현은 inframorph에서 작업한다.

기존 25개 사례를 유지하고 정상/위반 입력을 한 쌍씩 추가한다. 이 문서에서는 실제 fixture, manifest 기대값, 기존 통과 결과를 변경하지 않는다.

## 추가할 사례

| 묶음 | 정상 | 위반 또는 미지원 | 소비 규칙 |
| --- | --- | --- | --- |
| worker | 실제 진입 파일·관련 근거 | 파일 없음, 무관한 근거, 동적 명령 | I-001/I-002 |
| DB | datasource와 engine 일치 | provider 주장 불일치 | I-003 |
| 요구 누락 | 지원 패턴에서 확인한 요구 포함 | 확인된 worker/DB 요구를 Intent에서 누락 | I-005 |
| 설정 | 승인 config | secret/reserved 충돌, 실행 옵션, 미지원 일반 설정 | I-006 |
| Prisma | provider 전환만 수행 | 모델 필드/index/default 삭제·변경 | P-003 |
| storage | 승인된 호출 변환 | 같은 허용 파일의 인증/응답 로직 변경 | P-004 |
| 구문 | 일반 주석 속 금지어 | 실제 금지 호출/import | P-006 |
| 공개 범위 | web 1개·worker 비공개 | worker/DB 공개 또는 Plan 불일치 | L-002/L-003 |

사례별 ID·원본·최소 변경·기대 decision/reason_code·규칙 ID를 기록한다. manifest 기존 형식과의 호환성을 먼저 확인하고 필요하면 버전을 명시한다. 정상 앱이지만 미지원인 경우를 공격 성공/실패에 섞지 않는다.

## 실제 검증 순서

1. 비실행 fixture만 추가하고 정합성 검사를 수행한다.
2. 미구현 규칙에 대한 사례는 아직 실제 Gate 통과/차단 검증을 완료했다고 표시하지 않는다.
3. inframorph 구현을 통해 전체 사례를 실행한다. allow/reject와 PASS/BLOCK/UNSUPPORTED/ERROR 간 매핑을 명시한다.
4. 기대 판정뿐 아니라 규칙·사유 코드도 확인한다. 기존 25개 사례 누락 여부를 확인한다.
5. 검토된 이 브랜치 commit을 먼저 push한 뒤 inframorph에서 해당 SHA를 pin한다.
6. 두 저장소 PR을 연결하고 UI에 표시되는 실제 정책 결과까지 inframorph에서 확인한다.

source 검사 후 변조, 과거 PASS 재사용, Builder/Adapter 호출 차단, UI 새로고침/SSE 검증은 inframorph의 실행 테스트로 수행한다. 이 저장소의 정적 fixture만으로 증명하지 않는다.

## 완료 체크

- [ ] 기존 25개 사례 보존.
- [ ] 정상/위반/미지원 기대값 분리.
- [ ] 규칙별 최소 차이 쌍 추가.
- [ ] fixture 정합성 검사 통과.
- [ ] 고정 SHA로 inframorph 실제 Gate 검증 통과.
- [ ] 신규 case 수·사유 코드·미실행 수 보고.
- [ ] 연결된 UI가 실제 판정을 정확히 표시.

## 이번 변경

39개 사례(기존 25 + 신규 14)를 등록했다. config 정상/secret 충돌/실행 옵션/미지원 설정, DB provider/근거/누락, worker 정상/없는 파일/무관한 근거, Prisma 필드 삭제/default 변경, 무관한 storage 변경, 주석 오탐 통제를 포함한다. 독립된 기대값 및 변경 내용 검사와 40개 저장소 테스트가 통과했다. 실제 Gate 결과는 소비 저장소의 고정 SHA 검증 기록으로 확인한다.
