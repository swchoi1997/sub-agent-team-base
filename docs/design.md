# AI 에이전트 회사 템플릿 설계 (v2 초안)

> 목표: 어떤 프로젝트(신규·기존)에도 플러그인 설치 + `/company:init` 한 번으로 붙여 쓰는 "서브에이전트 기반 회사".
> 서비스 요청 한 번 → 기획 → 사람 검토 1회 → 기능별 개발·QA 자동 진행 → 완료 보고.

상태: **설계 합의 중** — 아래 "결정 사항"은 확정, "미결 사항"은 대화로 정한다.

---

## 1. 결정 사항 (합의 완료)

| 항목 | 결정 |
|---|---|
| 배포 | 이 레포 = 플러그인 마켓플레이스. 플러그인 이름 `company`. 프로젝트별 파일은 `/company:init`이 생성 |
| 실행 환경 | 로컬 터미널·클라우드 둘 다 지원. 중첩 깊이를 감지해 **팀장 모드 / 평면 모드** 자동 선택 |
| 스택 | 에이전트는 스택 중립. 스택·명령·컨벤션은 `docs/company/profile.md`(init이 자동 생성) |
| 팀 | 기획·개발·QA·마케팅 4개 팀 |
| Git | 요청마다 작업 브랜치 1개 + QA 합격한 기능마다 커밋. PR은 사람이 직접 |
| 추가 승인 | ① 위험 작업 전 ② 마케팅 산출물 (끝에서 일괄) |
| 모델 | 팀장·리뷰어 opus, 나머지 sonnet |
| QA 기준 | 테스트 실행 + 네거티브 테스트 + 코드 리뷰 + **앱을 실제로 띄워** 완료 기준 확인, 증거를 보고서에 기록 |
| 문서 | 요청(run)별 폴더 + 누적 공용 문서 |
| 언어 | 프롬프트 영어, 산출물·보고 한국어 (profile에서 변경 가능) |
| 마케팅 산출물 | 포지셔닝·메시지, 출시·채널 계획, 릴리즈 노트 |

---

## 2. 사용자 경험

```bash
# 최초 1회 (사용자 PC)
/plugin marketplace add swchoi1997/sub-agent-team-base
/plugin install company@sub-agent-team-base

# 프로젝트마다 1회
/company:init            # 프로젝트 분석 → profile.md, CLAUDE.md 섹션 생성

# 일할 때
/company:run "이런 서비스 만들어줘"   # 기획 → ★검토 → 기능 루프 → 완료 보고
/company:feature "결제 기능 추가"     # 작은 기획 → 개발 → QA
/company:bugfix "로그인 500 에러"     # 개발 → QA (회귀 테스트 필수)
/company:resume                      # 끊긴 run 이어서
/company:status                      # 현재 run의 roadmap 표 출력
```

사람이 하는 일은 `run` 기준 두 번: 요청, 기획 검토 후 `/goal` 설정. 나머지는 예외 멈춤에서만.

---

## 3. 조직과 두 가지 실행 모드

```
메인 세션 = 총괄 (플로우 스킬 실행, 승인은 여기서만)
├ 기획팀장 plan-lead   → plan-researcher, plan-analyst, plan-planner
├ 개발팀장 dev-lead    → dev-backend, dev-frontend
├ QA팀장   qa-lead     → qa-tester, qa-reviewer
└ 마케팅   mkt-marketer (팀원 1명 → 팀장 없음)
```

### 왜 모드가 두 개인가
클라우드 세션은 `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`로 고정돼 있어 서브에이전트가 또 서브에이전트를 부를 수 없다(이 레포의 클라우드 세션에서 확인). 로컬 기본값은 3.

| 모드 | 조건 | 동작 |
|---|---|---|
| 팀장 모드 | depth ≥ 2 | 메인 → 팀장 에이전트 → 팀원. 팀원 상세는 팀장 컨텍스트에 갇힘 |
| 평면 모드 | depth = 1 | 메인이 팀장 **플레이북**을 직접 수행하고 팀원만 서브에이전트로 띄움 |

- 감지: 플로우 스킬의 동적 주입 `` !`echo ${CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH:-3}` ``
- **팀장 절차는 한 곳에만 쓴다:** `playbooks/<team>-lead.md`. 팀장 에이전트 본문은 "이 플레이북을 따르라" 한 줄 + 역할 정의. 평면 모드에서는 메인이 같은 파일을 읽는다 → 두 모드의 동작이 갈라지지 않음.
- 평면 모드는 메인 컨텍스트가 빨리 찬다 → 팀원 보고 10줄 제한을 더 엄격히, 상세는 파일로.

---

## 4. 플러그인 구조 (이 레포)

```
.claude-plugin/marketplace.json
plugins/company/
  .claude-plugin/plugin.json
  agents/                       # 팀장 3 + 팀원 8
    plan-lead.md  plan-researcher.md  plan-analyst.md  plan-planner.md
    dev-lead.md   dev-backend.md      dev-frontend.md
    qa-lead.md    qa-tester.md        qa-reviewer.md
    mkt-marketer.md
  skills/                       # 사용자 진입점 (모두 disable-model-invocation: true)
    init/SKILL.md   run/SKILL.md   feature/SKILL.md
    bugfix/SKILL.md resume/SKILL.md status/SKILL.md
  playbooks/                    # 팀장 절차 (두 모드 공용)
    plan-lead.md  dev-lead.md  qa-lead.md
  templates/                    # init·run이 복사하는 문서 틀
    profile.md  product.md  prd.md  roadmap.md  qa-report.md  claude-md-section.md
docs/design.md                  # 이 문서
```

- 플러그인 훅은 모든 세션에 전역 적용되므로 **v1은 훅 없음**.
- 플러그인 에이전트는 `hooks`, `mcpServers`, `permissionMode`를 무시한다 → 필요한 프로젝트는 `.claude/agents/`로 복사해 덮어쓰기(같은 이름이면 프로젝트 쪽 우선 여부 검증 필요).

---

## 5. 프로젝트에 생기는 파일 (`/company:init`)

```
CLAUDE.md                         # 기존 내용 유지, <!-- company:start/end --> 사이에만 삽입
docs/company/
  profile.md                      # 스택, 빌드·테스트·실행·린트 명령(실제로 돌려서 검증), 컨벤션,
                                  # QA 수준, 산출물 언어, 위험 작업 목록
  product.md                      # 현재 제품 개요·기능 목록 (run이 끝날 때마다 갱신)
  api-contract.md                 # 누적 API 계약
  runs/
    001-mvp/
      request.md  research.md  analysis.md  prd.md  roadmap.md
      qa/F1.md  qa/F2.md ...      # 기능별 QA 증거
      marketing/positioning.md  launch-plan.md  release-notes.md
      log.md                      # 결정·멈춤·재작업 이력
  ACTIVE                          # 진행 중 run 폴더 이름 한 줄
```

- 기존 프로젝트: 코드베이스를 분석해 profile·product를 채운다. 명령은 실제로 실행해 통과/실패를 기록.
- 신규 프로젝트: profile의 스택은 `미정`. 기획팀이 제안하고 기획 검토에서 확정.
- `docs/` 바로 아래가 아니라 `docs/company/` 아래에 둬서 기존 문서와 충돌하지 않게 한다.

---

## 6. `/company:run` 흐름

```
0. 사전 점검   profile 없으면 init 안내 / 작업 트리 깨끗한지 / 브랜치 company/NNN-slug 생성 / run 폴더 생성
1. 기획        plan-lead: researcher ∥ analyst → planner(prd, roadmap) → 자체 검토
2. ★ 기획 검토  PRD 요약 + roadmap 표 + 위험 작업 목록 제시 → 수정 요청은 plan-lead로
               승인 = 사용자가 /goal 설정 (스킬이 goal 문장을 만들어 보여줌)
3. 마케팅       백그라운드로 mkt-marketer: 포지셔닝, 출시·채널 계획
4. 기능 루프    roadmap에서 의존이 충족된 첫 '대기' 기능:
                 dev-lead → qa-lead → 불합격이면 재작업(최대 2회) → 합격 → 커밋
                 → roadmap 갱신 → 표 출력 → 남은 기능 있으면 보고 없이 다음
5. 마무리       mkt-marketer: 릴리즈 노트 → ★ 마케팅 산출물 검토 → product.md 갱신 → 완료 보고
```

### roadmap.md 형식
```markdown
| # | 기능 | 의존 | 완료 기준 | 위험 | 상태 | QA |
|---|---|---|---|---|---|---|
| F1 | 회원가입/로그인 | - | 이메일 가입 후 재접속 시 로그인 유지 | DB 스키마 생성(사전승인) | 완료 | 합격 (qa/F1.md) |
| F2 | 프로필 | F1 | 수정 후 새로고침해도 유지 | - | 진행 | - |
```
- 상태값: `대기 / 진행 / 재작업1 / 재작업2 / 승인대기 / 완료 / 보류`
- **위험 열**: 기획 단계에서 예상되는 위험 작업을 미리 적고, 기획 검토 때 사전 승인받는다 → 루프 중 멈춤 최소화. 예상 못 한 위험 작업이 나오면 `승인대기`로 멈춤.

### 멈춤 조건
1. 재작업 2회 후에도 QA 불합격
2. 스펙 모순 발견 (개발·QA가 기획으로 되돌림 요청)
3. 사전 승인되지 않은 위험 작업 (profile의 위험 작업 목록 기준)
4. 검증 불가 — 앱을 띄우거나 테스트를 돌릴 수 없는 환경 문제

멈출 때는 log.md에 사유를 쓰고, roadmap 상태를 바꾸고, 표와 함께 보고. `/company:resume`로 재개.

### /goal 문장 (스킬이 생성)
```
docs/company/runs/001-mvp/roadmap.md 의 모든 기능 상태가 "완료"이고 QA 열이 모두 "합격"이며,
마지막 응답에 그 roadmap 표가 출력되어 있다
```

---

## 7. 팀별 업무 정의 (검증 가능한 행동)

| 에이전트 | 하는 일 | 산출물 | 도구 요점 |
|---|---|---|---|
| plan-lead | 팀원 분배, PRD·roadmap 자체 검토(완료 기준이 검증 가능한가, 의존 순환 없음, 위험 열 기입, 신규면 스택 제안) | 검토 결과 보고 | Agent, Read, Write |
| plan-researcher | 시장·경쟁·사용자 조사, 모든 주장에 출처 URL | research.md | WebSearch, WebFetch |
| plan-analyst | 요구사항 분석. 기존 프로젝트면 영향 받는 코드·제약 분석 | analysis.md | Read, Grep, Glob |
| plan-planner | PRD + roadmap 작성 | prd.md, roadmap.md | Read, Write |
| dev-lead | 기능 범위 확인, API 계약 작성, 필요한 팀원만 병렬 위임, 계약 일치·빌드 통과 확인 | api-contract.md 갱신 | Agent, Bash(빌드·테스트만), Read, Write |
| dev-backend / dev-frontend | profile 규칙대로 구현 + 단위 테스트 | 코드, 테스트 | Read, Write, Edit, Bash |
| qa-lead | 팀원 결과 종합, 합격/불합격 판정 | qa/Fn.md | Agent, Read, Write |
| qa-tester | 테스트 실행, 네거티브 테스트 1건 이상 추가, 앱 실행 후 완료 기준을 curl/Playwright로 확인 | 증거표 | Bash, Read, Write |
| qa-reviewer | 변경 diff 리뷰(정확성·보안·계약 일치) | 리뷰 항목 | Read, Grep, Bash(git diff) |
| mkt-marketer | 포지셔닝, 출시·채널 계획, 릴리즈 노트 | marketing/*.md | WebSearch, Read, Write |

원칙
- QA는 코드를 고치지 않는다. 증거와 판정만.
- 각 단계는 시작 전에 이전 단계의 완료 기준을 다시 확인한다 (일방향 넘기기 금지).
- 보고 형식 고정: `완료 / 변경 파일 / 남은 이슈 / 다음 단계에 필요한 것`, 10줄 이내.
- 재작업은 `SendMessage`(에이전트 ID)로 기존 팀원에게. 쓸 수 없으면 이전 보고 + 불합격 항목을 넣어 새로 위임.

---

## 8. 조사로 확인한 제약 (공식 문서 기준)

| 사실 | 설계 영향 |
|---|---|
| `tools: Agent(a, b)`의 허용 목록은 `claude --agent`로 메인 스레드일 때만 적용, 서브에이전트 정의 안에서는 무시된다는 문서 요약 | 팀 경계는 **프롬프트 규칙**으로 1차 통제. 구현 때 실제 동작 검증 |
| depth 한도에 닿으면 서브에이전트에서 Agent 도구가 빠짐 | 평면 모드 필요성 확인 |
| 플러그인 에이전트는 `hooks`, `mcpServers`, `permissionMode` 무시 | v1은 이 필드에 의존하지 않음 |
| 스킬·에이전트 본문에서 `${CLAUDE_PLUGIN_ROOT}` 치환됨 | 플레이북·템플릿 경로 참조에 사용 |
| 스킬 `` !`cmd` `` 동적 주입 | 모드 감지, ACTIVE run 읽기 |
| SendMessage는 에이전트 팀 없이 ID로 이어 쓰기 가능 | 재작업 방식 유지 |
| `/goal`은 이번 조사 범위 문서에 없음 | 구현 때 실제 동작 확인, 안 되면 "보고 없이 계속" 규칙만으로 루프 |

---

## 9. 2차 결정 사항

| 항목 | 결정 |
|---|---|
| `/company:feature` 승인 | 짧은 스펙(범위·완료 기준·위험, 5줄 안팎) 승인 후 개발 시작 |
| 릴리즈 노트 | 모든 기능 완료 후 roadmap·커밋 기록으로 일괄 작성 |
| 병렬 개발 | v1은 순차. 안정화 후 worktree 병렬 검토 |
| 파일럿 | 이 레포 `examples/`에 작은 샘플 앱을 두고 `/company:run`으로 신규 흐름 검증 |

### 남은 미결
- [ ] 파일럿 샘플 앱의 스택
- [ ] 위험 작업 기본 목록 확정 (안: DB 마이그레이션, 대량 삭제, 의존성 메이저 업그레이드, 결제·배포·외부 API 연동, 시크릿 변경)

---

## 10. 구현 순서 (제안)

1. 플러그인 골격 + marketplace.json
2. templates + `/company:init` → 빈 프로젝트·기존 프로젝트 각각에서 profile 생성 확인
3. 에이전트 11개 + 플레이북 3개
4. `/company:bugfix` (가장 짧은 흐름)로 개발·QA 고리 검증
5. `/company:feature` → `/company:run` 순서로 확장
6. 두 모드(depth 1 / 3) 모두에서 파일럿 실행, 토큰·시간 기록
7. 이후: ultracode와 비교 (가이드 12번)
