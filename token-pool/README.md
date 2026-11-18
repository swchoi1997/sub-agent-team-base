# tokenpool — 팀 사내 LLM 토큰 공유 프록시

사내 LLM 키는 사람마다 **하루 토큰 한도**가 있고, 쓰지 않으면 그날 사라집니다.
tokenpool은 팀원의 키를 공유 DB에 모아 두고, Claude Code 요청마다 쓸 키를 자동으로 고르는 **로컬 프록시**입니다.
내 한도를 다 쓰면 연차 중인 사람의 키, 그다음 덜 쓴 팀원의 키로 자동으로 넘어갑니다.

```
Claude Code ──(ANTHROPIC_BASE_URL=http://127.0.0.1:8787, 더미 키)──▶ tokenpool serve ──(고른 실제 키)──▶ 사내 LLM
                                                                     │
                                                                     └── 공유 DB (암호화된 키 · 오늘 사용량 · 연차 · 사용 로그)
```

Claude Code 자체는 수정하지 않습니다. `ANTHROPIC_BASE_URL`만 로컬 프록시로 바꿉니다.

## 키 선택 규칙

1. **내 키** → **오늘 연차 등록한 사람의 키** → **나머지 팀원 키** 순서로 고릅니다. 같은 그룹 안에서는 오늘 덜 쓴 키가 먼저입니다.
2. 사내 LLM이 **429**를 돌려주면:
   - `retry-after`가 짧으면(기본 600초 이하) 일시적인 rate limit으로 보고, 그 시간만큼만 키를 쉬게 합니다.
   - 그렇지 않으면 **오늘 한도 소진**으로 기록하고 즉시 다음 키로 다시 시도합니다. 사용자는 오류를 보지 않습니다.
   - 소진 기록은 날짜 단위라서 자정(기본 `Asia/Seoul`)이 지나면 자동으로 풀립니다.
3. **401**(키 무효)이 나면 그 키를 오늘 풀에서 뺍니다. 그 밖의 오류(400, 403, 5xx 등)는 그대로 전달합니다.
   네트워크 오류일 때는 키를 막지 않습니다.
4. **본인 몫 보호**: 키가 처음 429를 받을 때까지 쓴 누적량을 그 키의 *추정 한도*로 학습합니다.
   그 뒤로는 출근한 팀원의 키를 다른 사람이 추정 한도의 50%(`borrow_ratio`)까지만 빌려 씁니다. 연차인 사람의 키는 끝까지 씁니다.
5. **세션 고정**: 남의 키를 빌려 쓰는 동안에는 직전에 성공한 키를 계속 씁니다(서버 측 프롬프트 캐시 유지).
6. 모든 키를 쓸 수 없으면 Anthropic 형식의 429 오류를 돌려줍니다.

> 추정 한도는 tokenpool을 거친 사용량만 셉니다. 누군가 같은 키를 프록시 없이 따로 쓰면 한도가 실제보다 작게 학습됩니다.
> 이 경우 보호가 더 보수적으로 동작할 뿐 위험하지는 않습니다.

## 설치

```bash
pip install ./token-pool                 # SQLite만으로 시험해 볼 때
pip install "./token-pool[postgres]"     # 공유 DB가 Postgres일 때 (MySQL은 [mysql])
```

Python 3.11 이상이 필요합니다.

## 시작하기

### 1) 팀에서 한 번: 시크릿과 DB 준비

```bash
tokenpool gen-secret      # 출력된 값을 팀원끼리만 안전하게 공유
```

공유 DB(예: `postgresql+psycopg://tokenpool:pw@db-host/tokenpool`)를 하나 만듭니다. 테이블은 처음 `init`할 때 자동으로 생깁니다(`tp_` 접두어).

### 2) 팀원 각자

```bash
export TOKENPOOL_SECRET=<팀 시크릿>       # 셸 프로필에 넣어 두세요
tokenpool init --name 김철수 \
  --db-url postgresql+psycopg://tokenpool:pw@db-host/tokenpool \
  --upstream https://llm.internal.example.com
# → 사내 LLM API 키를 입력하면 암호화해서 풀에 등록합니다
```

- 사내 LLM이 `Authorization: Bearer`로 키를 받으면 `--auth-header authorization`을 붙이세요(기본은 `x-api-key`).
- 설정은 `~/.tokenpool/config.toml`에 저장됩니다(경로를 바꾸려면 `TOKENPOOL_CONFIG`).

`~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8787",
    "ANTHROPIC_AUTH_TOKEN": "tokenpool-local"
  }
}
```

`ANTHROPIC_AUTH_TOKEN`은 더미 값입니다. 프록시가 이 값을 지우고 실제 키로 바꿔 넣습니다.

```bash
tokenpool serve            # 켜 둔 상태로 Claude Code 사용
```

## 명령

| 명령 | 설명 |
|---|---|
| `tokenpool leave` | 오늘 연차 등록 → 오늘 내 키를 팀이 먼저 씀 |
| `tokenpool leave 2026-12-24 --to 2026-12-26` | 기간 등록 (`--cancel`로 취소) |
| `tokenpool status` | 오늘 키별 사용량·상태·추정 한도, 누가 누구 키를 빌려 썼는지 |
| `tokenpool disable` / `enable` | 내 키를 풀에서 빼기 / 다시 넣기 |
| `tokenpool unblock 이름` | 소진으로 잘못 처리된 키를 오늘 다시 사용 가능으로 |
| `tokenpool init` | 다시 실행하면 키 교체 (추정 한도 초기화) |

`status` 예시:

```
[2026-11-18] 팀 토큰 풀 현황 (기준 시간대 Asia/Seoul)

 이름        상태             오늘 사용   요청  추정 한도
---------------------------------------------------------
*김철수      오늘 소진              516      4        516
 박민수      사용 가능                0      0          -
 이영희      연차(공유 우선)         26      1          -

빌려 쓴 내역 (키 소유자 ← 실제 사용자)
  이영희 ← 김철수: 26 토큰 / 1회
```

## 설정 (`config.toml`)

| 키 | 기본값 | 설명 |
|---|---|---|
| `auth_header` | `x-api-key` | 사내 LLM이 키를 받는 헤더. `authorization`이면 Bearer |
| `port` | `8787` | 로컬 프록시 포트(`127.0.0.1`에만 바인딩) |
| `timezone` | `Asia/Seoul` | 일일 한도가 초기화되는 시간대 |
| `borrow_ratio` | `0.5` | 출근한 팀원 키를 남이 쓸 수 있는 비율(추정 한도 기준) |
| `max_attempts` | `6` | 요청 하나당 시도할 최대 키 수 |
| `short_cooldown_max` | `600` | 이 값(초) 이하의 `retry-after`는 일시 제한으로 처리 |

## 주의사항

- **보안**: 이 구조(로컬 프록시 + 공유 DB)에서는 DB 접속 정보와 `TOKENPOOL_SECRET`을 가진 팀원이면 누구나 모든 키를 복호화할 수 있습니다.
  팀 내부 신뢰를 전제로 합니다. DB 계정은 팀원에게만 주고, 시크릿은 메신저 대화방에 남기지 마세요.
  나중에 키를 PC에 아예 내리지 않으려면, DB 앞에 작은 키 브로커 API를 두는 구조로 바꾸면 됩니다.
- **사내 정책**: 사내 LLM 감사 로그에는 **키 소유자**가 쓴 것으로 남습니다. 본인 동의(opt-in)한 사람만 등록하고,
  실제 사용자는 `tp_usage_log`와 `tokenpool status`로 확인하세요. 사내 규정상 키 공유가 금지돼 있다면 운영팀과 먼저 협의하세요.
- 프롬프트·응답 내용은 DB에 저장하지 않습니다. 모델 이름과 토큰 수만 기록합니다.

## 개발 / 테스트

```bash
cd token-pool
pip install -e ".[test]"
pytest
```

가짜 사내 LLM(키별 한도를 넘기면 429)으로 직접 돌려 볼 수도 있습니다.

```bash
MOCK_KEYS="key-kim:400,key-lee:100000" uvicorn tests.mock_upstream:app --port 9900
tokenpool init --upstream http://127.0.0.1:9900 --db-url sqlite:///pool.db ...
tokenpool serve
```
