# 프로젝트 프로필

<!-- company:profile template_version: 1 -->
<!-- /company:init 이 생성하고 사람이 확인한다. 모든 company 에이전트가 가장 먼저 읽는 파일. -->

## 기본
- 유형: <신규 | 기존>
- 한 줄 설명: <이 프로젝트가 무엇인지>
- 산출물 언어: ko
- 모드 메모: <로컬 터미널 / 클라우드 등 주 실행 환경>

## 스택
| 영역 | 기술 | 버전 | 근거(파일) |
|---|---|---|---|
| backend | <예: Spring Boot (Java 21, Gradle)> | | <build.gradle> |
| frontend | <예: React + Vite + TypeScript> | | <frontend/package.json> |

신규 프로젝트는 `미정`으로 두고, 기획 검토에서 확정한 뒤 F0 완료 시 채운다.

## 개발 역할 (켤 역할만 남긴다)
| 역할 | 에이전트 | 담당 경로 |
|---|---|---|
| backend | company:dev-backend | <backend/**> |
| frontend | company:dev-frontend | <frontend/**> |
| mobile | company:dev-mobile | <mobile/**> |
| infra | company:dev-infra | <build files, CI, docker, scripts> |

공용 파일 담당: <예: 루트 build 파일·docker-compose → infra, 없으면 backend>

## 명령 (init 이 실제로 실행해 결과를 기록)
| 용도 | 명령 | 작업 디렉터리 | 마지막 결과 |
|---|---|---|---|
| build | <./gradlew build -x test> | <backend> | <성공/실패/미검증 + 날짜> |
| test | <./gradlew test> | <backend> | |
| test (frontend) | <npm test -- --run> | <frontend> | |
| lint | <npm run lint> | <frontend> | |
| run (dev) | <./gradlew bootRun> | <backend> | |

## QA 실행 프로필 (임시 DB로 앱 기동)
- docker 있을 때: <예: docker compose -f docker-compose.qa.yml up -d && SPRING_PROFILES_ACTIVE=qa ./gradlew bootRun>
- docker 없을 때: <예: SPRING_PROFILES_ACTIVE=qa-embedded ./gradlew bootRun  (H2 PostgreSQL 모드)>
- 종료 방법: <예: docker compose -f docker-compose.qa.yml down -v>
- 확인 URL: <http://localhost:8080/actuator/health, http://localhost:5173>

## DB 목록
| 이름 | 종류 | 위치 | temporary | 비고 |
|---|---|---|---|---|
| <qa-db> | <postgres> | <QA 프로필 컨테이너> | yes | 테스트가 띄우고 지움 |
| <local-dev> | <postgres> | <localhost:5432> | no | SELECT 만 자유 |

목록에 없는 DB는 영구 DB로 간주한다 (SELECT 외 승인 필요).

## 컨벤션
- 코드 스타일: <린터/포매터, 기존 규칙 문서 경로>
- 커밋 메시지: <예: Conventional Commits, 영어>
- 코드 주석 언어: <예: 영어>
- 브랜치: company/<NNN-slug>
- API 계약 정본: <docs/company/api-contract.md | openapi.yaml 경로>

## 제한 의존성 (추가·제거 시 승인)
- <없음>

## 추가 승인 항목
- <없음>

## 사용자 설치 권장 도구 (선택)
- Context7 MCP, Playwright MCP, 스택별 LSP 플러그인
