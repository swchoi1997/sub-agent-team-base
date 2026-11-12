# 파일럿: Spring Boot + React 할 일 관리 서비스

템플릿 전체 흐름을 검증하기 위한 시나리오입니다. 이 폴더에는 아직 앱 코드가 없습니다.
아래 순서로 `company` 플러그인이 직접 만들게 하는 것이 검증 그 자체입니다.

## 준비

```bash
mkdir -p ~/todo-pilot && cd ~/todo-pilot && git init && echo "# todo pilot" > README.md && git add . && git commit -m init
claude --plugin-dir <이 레포 경로>/plugins/company     # 또는 플러그인 설치 후 claude
```

## 1. 신규 프로젝트 흐름

```
/company:init
/company:run "개인용 할 일 관리 웹 서비스. 백엔드 Spring Boot(Java 21, Gradle), 프론트엔드 React(Vite, TypeScript).
회원가입·로그인, 할 일 CRUD, 완료 표시, 마감일 필터. DB는 PostgreSQL, 테스트와 QA는 임시 DB로."
```

확인할 것:

| 단계 | 기대 결과 |
|---|---|
| init | 유형 `신규`, 스택 `미정`, 모드(깊이 1 → flat / 3 → lead), Docker 유무 기록, db-guard 자체 테스트 통과 |
| 기획 | roadmap 첫 행이 `F0 프로젝트 골격`, 모든 완료 기준이 실행 가능한 형태, 위험 열에 "로컬 DB 마이그레이션 적용" 같은 항목 |
| 검토 | PRD 요약 + roadmap + 위험 목록 + 스택 제안이 한 화면에, `/goal` 문장 제시 |
| F0 | 골격·테스트 하네스·QA 실행 프로필(Docker 없으면 H2/embedded) 생성 후 profile 명령이 채워짐 |
| 루프 | 기능마다 `qa/Fn.md` 증거표, 커밋 관문, 커밋, roadmap 표 출력, 묻지 않고 다음 기능 |
| 승인 | DB 쓰기·마이그레이션 실행 시 `승인대기`로 멈추고 질문, 승인 후 메인이 실행 |
| 마무리 | 릴리즈 노트 → 마케팅 검토 → product.md 갱신 → ACTIVE 삭제 |

## 2. 기존 프로젝트 흐름 (같은 결과물 위에서)

```
/company:feature "할 일에 태그를 붙이고 태그로 필터링"
/company:bugfix "마감일이 오늘인 할 일이 '지난 할 일' 필터에 나온다"
```

확인할 것: feature는 5줄 스펙 승인 후 진행, bugfix는 재현 테스트가 먼저 실패하는지.

## 3. 기록할 측정값 (비교 실험용)

각 run의 `docs/company/runs/<run>/log.md` 측정 표: 기능별 모드, 소요 시간, 서브에이전트 토큰, 재작업 횟수.
같은 요청을 lead 모드(로컬, 깊이 3)와 flat 모드(클라우드, 깊이 1)로 한 번씩, 이후 `ultracode`로도 돌려 비교합니다.
