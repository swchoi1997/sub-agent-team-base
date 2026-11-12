# sub-agent-team-base — `company` 플러그인

Claude Code 서브에이전트로 "AI 회사"를 꾸려 프로젝트를 진행하는 플러그인입니다.
서비스 요청 한 번이면 기획팀이 PRD와 로드맵을 만들고, 사람이 한 번 검토한 뒤,
기능마다 개발팀 → QA팀 → 커밋을 자동으로 반복합니다. 신규 프로젝트와 기존 프로젝트 모두에 붙여 쓸 수 있습니다.

## 설치

```
/plugin install company --marketplace swchoi1997/sub-agent-team-base
```

(이전 버전 Claude Code: `/plugin marketplace add swchoi1997/sub-agent-team-base` → `/plugin install company@sub-agent-team-base`)

## 사용

```
/company:init                         # 프로젝트마다 1회: 분석 → docs/company/profile.md, CLAUDE.md 섹션, db-guard 훅
/company:run "이런 서비스 만들어줘"    # 기획 → ★검토 → 기능별 개발·QA·커밋 → 마케팅 검토 → 완료 보고
/company:feature "결제 기능 추가"      # 짧은 스펙 → ★승인 → 개발·QA·커밋
/company:bugfix "로그인 500 에러"      # 재현 테스트 → 원인 분석·수정 → QA → 커밋
/company:resume                       # 멈춤·승인·세션 끊김 후 이어서
/company:status                       # 현재 roadmap 표와 멈춤 사유
```

기획 검토가 끝나면 스킬이 `/goal` 문장을 보여줍니다. 자리를 비울 때 그 문장으로 `/goal`을 설정하면 끝까지(또는 멈춤 조건까지) 진행합니다.

## 조직

```
메인 세션 = 총괄 (승인·위험 작업 실행·커밋은 여기서만)
├ 기획팀장 plan-lead → plan-researcher, plan-analyst, plan-planner
├ 개발팀장 dev-lead  → dev-backend, dev-frontend, dev-mobile, dev-infra (profile에서 켠 역할만)
├ QA팀장   qa-lead   → qa-tester, qa-reviewer
└ 마케팅   mkt-marketer
```

- **팀장 모드 / 평면 모드 자동 선택**: 서브에이전트 중첩 깊이가 2 이상이면 팀장이 팀원을 지휘하고,
  1이면(클라우드 세션 등) 메인 세션이 같은 팀장 플레이북을 직접 수행합니다.
- **승인 정책**: DB는 SELECT만 자유, 나머지는 전부 사람 승인(임시 테스트 DB 예외). 서브에이전트는 승인 대상을
  실행하지 않고 보고하며, 메인 세션이 승인받아 실행합니다. 프로젝트의 db-guard 훅이 DB 쓰기·마이그레이션 명령에
  권한 확인을 한 번 더 띄웁니다.
- **품질 관문**: QA는 테스트 + 네거티브 테스트 + 앱 실제 기동 확인 + 코드 리뷰 + 위험 변경 감사, 커밋 전에는 메인이
  테스트를 직접 다시 돌립니다. push와 PR은 사람이 합니다.

## 구성

| 경로 | 내용 |
|---|---|
| `.claude-plugin/marketplace.json` | 마켓플레이스 |
| `plugins/company/agents/` | 에이전트 13개 |
| `plugins/company/skills/` | `/company:*` 스킬 6개 |
| `plugins/company/playbooks/` | 공통 규칙, 총괄·팀장 절차 (두 모드 공용) |
| `plugins/company/templates/` | profile, prd, roadmap, qa-report, log 등 문서 틀 |
| `plugins/company/project-hooks/` | init이 프로젝트에 설치하는 db-guard 훅 |
| `plugins/company/vendor/` | 복사한 외부 스킬 (superpowers, anthropics/skills, marketingskills — 출처·라이선스는 `vendor/README.md`) |
| `docs/design.md` | 설계 문서 |
| `examples/` | 파일럿 안내 |
| `tests/` | db-guard 훅 테스트 (`bash tests/db-guard.test.sh`) |

## 개발

```
claude plugin validate .                 # 마켓플레이스·플러그인 검증
bash tests/db-guard.test.sh              # 훅 테스트
claude --plugin-dir ./plugins/company    # 설치 없이 로컬 플러그인으로 실행
```

## 라이선스

MIT. `plugins/company/vendor/` 아래 파일은 각 원본 라이선스(MIT, Apache-2.0)를 따릅니다.
