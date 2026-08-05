# 두 에이전트 동기화 규약

두 채팅이 같은 저장소를 서로 다른 브랜치에서 작업한다. 이 폴더는 둘 사이의
**우편함**이고, `sync_check.py`가 배달부이자 검사관이다.

| | 에이전트 1 | 에이전트 2 |
|---|---|---|
| 담당 | 논문 조사·물성 정리 | 코드 작성·해석 결과 |
| 브랜치 | `claude/paper-reference-research-pksw5p` | `claude/thesis-csic-thermal-shock-5m53iv` |
| 약칭 | `a1` | `a2` |

---

## 1. 규칙 — 파일 하나에 주인은 하나

**자기 소유가 아닌 파일은 절대 편집하지 않는다.** 이것만 지키면 두 브랜치를
언제 병합해도 이 폴더에서는 충돌이 나지 않는다 (git은 서로 다른 파일의 변경을
자동으로 합친다).

| 파일 | 주인 | 내용 |
|---|---|---|
| `sync/outbox_a1.json` | **a1** | a1 → a2 로 보내는 메시지 |
| `sync/state_a1.json` | **a1** | a1이 a2의 메시지를 어디까지 읽었는지 |
| `sync/outbox_a2.json` | **a2** | a2 → a1 로 보내는 메시지 |
| `sync/state_a2.json` | **a2** | a2가 a1의 메시지를 어디까지 읽었는지 |
| `sync/sync_check.py` | **a2** | 도구 (a1은 읽어서 실행만, 편집 금지) |
| `sync/PROTOCOL.md` | **a2** | 이 문서 |

> **왜 a2가 도구를 소유하나.** 사용자가 정한 역할 그대로다 — a2가 코드 담당이다.
> a1이 이 도구를 고쳐야 할 일이 생기면, 고치지 말고 `outbox_a1.json`에
> `kind: "question"` 메시지로 요청한다.

---

## 2. 메시지 형식

각 outbox는 다음 모양의 JSON 하나다. `messages`는 **덧붙이기만** 한다 — 이미
보낸 메시지를 지우거나 고치지 않는다 (상대가 이미 읽고 조치했을 수 있다).
정정할 일이 있으면 `supersedes`를 단 **새 메시지**를 보낸다.

```json
{
  "agent": "a2",
  "branch": "claude/thesis-csic-thermal-shock-5m53iv",
  "messages": [
    {
      "id": "a2-0001",
      "date": "2026-08-04",
      "kind": "finding",
      "blocking": true,
      "subject": "한 줄 제목",
      "body": "무엇을, 왜, 상대가 뭘 해야 하는지",
      "action": "상대가 할 일 한 줄"
    }
  ]
}
```

### 필수 필드

| 필드 | 설명 |
|---|---|
| `id` | `a1-0001` / `a2-0001` … **순번은 되돌리지 않는다** |
| `date` | `YYYY-MM-DD` (KST) |
| `kind` | 아래 표 |
| `blocking` | `true`면 상대가 `--ack` 하기 전까지 **상대 쪽 검증이 실패**한다 |
| `subject` | 한 줄 |
| `body` | 상대가 앞뒤 맥락 없이 읽어도 이해되게 |
| `action` | 상대가 할 일. 없으면 `""` (참고용 통보) |

### 선택 필드

| 필드 | 언제 |
|---|---|
| `slot` | 카드 슬롯을 지목할 때: `{"card": "yarn", "index": 11}` (`matrix`/`yarn`/`macro`) |
| `lo`, `hi`, `unit` | `kind: "band"` — 독립 문헌 범위 |
| `value` | `kind: "value"` — 확정값 |
| `grade` | `fulltext` / `digitized` / `abstract` / `secondary` — **`band`·`value`에는 필수** |
| `source` | 출처 문자열. `grade`가 있으면 필수 |
| `supersedes` | 이 메시지가 대체하는 이전 `id` |

### `kind` 목록

| kind | 방향 | 뜻 |
|---|---|---|
| `band` | a1 → a2 | 카드 슬롯의 **독립** 문헌 범위. `check_card_ranges.py` 행이 된다 |
| `value` | a1 → a2 | 확정 물성값 + 출처 |
| `ref` | a1 → a2 | 새 참고문헌 번호 배정 (`refs/[NN]`) |
| `verdict` | a1 → a2 | 판정선·포락선 (예: CTE 상한) |
| `need` | a2 → a1 | 출처가 없는 슬롯 — a1의 작업 큐 |
| `finding` | a2 → a1 | 해석 결과가 문헌과 어긋남 |
| `changed` | a2 → a1 | 카드값·코드·규약이 바뀜 |
| `question` | 양방향 | 답이 필요함 |

> **`secondary` 등급은 논문에 인용할 수 없다** (CLAUDE.md). `band`/`value`로
> 보낼 수는 있으나 `action`에 "1차 출처 확보 필요"를 반드시 적는다.

---

## 3. 쓰는 법

```bash
# 상대가 새로 보낸 것 확인 (자동으로 상대 브랜치를 fetch 한다)
python3 sync/sync_check.py

# 읽고 조치했으면 기록
python3 sync/sync_check.py --ack a1-0003
python3 sync/sync_check.py --ack-all       # 전부

# 보낼 때는 자기 outbox JSON에 메시지를 덧붙인다 (직접 편집)
```

**`sync_check.py`는 커밋 전 검증 목록에 들어 있다.** 따라서 상대가 `blocking`
메시지를 보내면 **읽고 처리하기 전에는 커밋이 막힌다.** 이것이 "알아차림"의
실제 작동 방식이다 — 기억에 의존하지 않는다.

---

## 4. `band` 메시지는 **적용되었는지까지** 검사된다

`kind: "band"`에 `slot`과 `lo`/`hi`가 있으면, `sync_check.py`는
`verification/check_card_ranges.py`의 감사표에서 **그 범위가 실제로 반영되었는지**
찾는다. 없으면 `미적용`으로 보고한다.

즉 a1이 범위를 보내고 a2가 `--ack`만 하고 표를 안 고치면 **그 사실이 드러난다.**
`--ack`는 "읽었다"가 아니라 **"반영했다"**는 뜻으로 쓴다.

---

## 5. 병합할 때

이 폴더는 충돌하지 않지만, 나머지 저장소는 충돌할 수 있다. 병합 전에:

1. `python3 sync/sync_check.py` — 미처리 메시지가 없는지
2. 상대 브랜치의 검증 명령이 전부 통과하는지 (`CLAUDE.md` 목록)
3. **검증 항목 수는 손으로 더하지 않는다** — 스크립트 실제 출력에서 다시 센다

병합 후 `--ack-all`로 정리하고, 병합 사실 자체를 `kind: "changed"` 메시지로
상대에게 알린다.
