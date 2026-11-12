<!-- company:start (managed by /company:init — edit outside this block) -->
## AI 회사 (company 플러그인)

이 프로젝트는 `company` 플러그인의 서브에이전트 회사 구조로 작업한다.

- 프로필: `docs/company/profile.md` (스택, 명령, 개발 역할, QA 실행 프로필, DB 목록)
- 진행 중 run: `docs/company/ACTIVE` → `docs/company/runs/<run>/`
- 흐름: `/company:run` (서비스·큰 변경) · `/company:feature` (기능 1개) · `/company:bugfix` · `/company:resume` · `/company:status`
- 조직: 메인 세션(총괄) → 기획팀 · 개발팀 · QA팀 · 마케팅
- 승인: DB 는 SELECT 외 전부 사람 승인 (임시 테스트 DB 예외). 서브에이전트는 승인 대상을 실행하지 않고 보고한다.
- 코드 컨벤션은 이 프로젝트의 규칙이 우선, 진행 흐름과 승인은 company 규칙이 우선.
<!-- company:end -->
