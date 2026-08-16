# CDM-UMAT — 작업 규칙

석사학위논문 프로젝트. 개요는 `README.md`, 연구계획은 `docs/THESIS_PLAN.md`,
노벨티는 `docs/NOVELTY.md`.

---

## ★ 응답 형식 (사용자 지정, 2026-08-10 개정 — 모든 채팅에 항상 적용)

**모든 채팅 응답은 아래 다섯 부분을 이 순서로 갖춘다.** 질문이 짧든 작업이
길든, 코드 변경이 있든 없든 예외 없이 지킨다.
(2026-08-10 이전 순서는 답→다음할일→꼭→쉬운→진행도였다 — 사용자가 바꿨다.)

### 1) 🔋 진행도 — **맨 위**

게임 진행바처럼. 10단계 체크리스트 + 보조 지표. 형식 예:

```
🔋 진행도   █████████░░░░░░░░░░░   4.5 / 10 단계
   └ 6단계 「유효물성 = 거시 카드」  ██████░░░░  약 60 %
     ✅ 1 UMAT 구현      ✅ 2 코드 검증      ✅ 3 RVE+PBC
     ✅ 4 냉각/TRS       🔶 5 인장 검증      🔶 6 유효물성
     🔶 7 거시 열전달    ⬜ 8 9케이스        ⬜ 9 TRS 비교
     ⬜ 10 최종 확정
   코드 완성도  █████████▉  9.9 / 10   (검증 N / 명령 M)
   결과 추출    ████▌░░░░░  4.5 / 10
```

### 2) 질문에 대한 답

본문. 결론 먼저, 근거는 그 아래.

### 3) `## 꼭 읽어봐야하는 부분`

본문 재나열이 아니라 **결론과 숫자 위주로 압축**한다.
사용자가 이 섹션만 읽어도 판단할 수 있어야 한다.

### 4) `## 쉬운 설명`

전공 지식이 없어도 이해되게 비유를 써서 풀어 쓴다 — 전문용어 최소화.

### 5) `### 다음 할 일 추천` — **맨 끝**

**모든 채팅 응답에서 5가지 추천한다** (사용자 지정, 2026-08-11 — 이전에는
"작업을 끝낼 때마다 3가지"였다. 개수와 빈도가 둘 다 바뀌었다).

- 각 항목에 **왜 지금인지**와 **대략의 비용**을 한 줄로 붙인다.
- 해석 실행이 막혀 있는지와 무관하게 할 수 있는 일을 우선한다.
- **억지로 3개를 만들지 않는다.** 정말 없으면 "지금은 없다"고 말하고 이유를 적는다.

### 6) 본문은 `[챕터]` + 번호 한 줄 (사용자 지정, 2026-08-11)

위 2)·3)·4)의 **속을 채우는 방식**이다. 줄글 문단으로 길게 쓰지 않는다.

```
[무엇에 대한 이야기인가]
1. 한 문장.
2. 한 문장.
   2.1 길어지면 이렇게 쪼갠다.
   2.2 한 항목이 두 줄을 넘지 않게 한다.

[다음 이야기]
1. ...
```

- `[ ]` = **내용 하나당 챕터 하나**. 제목은 짧게.
- `1. 2. 3.` = **설명 한 줄씩**. 한 항목에 주장 하나만 담는다.
- 내용이 많으면 `1.1`·`1.2` 로 내린다. 3단계(`1.1.1`)까지는 가지 않는다.
- 표·코드블록은 이 규칙 밖이다 — 그대로 써도 된다.

### 7) 쉬운 단어로 쓴다 (사용자 지정, 2026-08-11)

**한자어 전문용어를 그대로 던지지 않는다.** 아래는 실제로 사용자가 막힌 말들이다.

| 쓰지 말 것 | 대신 |
|---|---|
| 연화 | 힘이 떨어지는 구간 / 무르는 것 |
| 소산 | 에너지가 빠져나가는 것 |
| 오귀속 | 출처를 잘못 붙인 것 |
| 일관접선 | (Abaqus가 요구하는) 강성 행렬, 수렴용 기울기 |
| 할선 | 원점에서 그은 기울기 |
| 접선 | 그 점에서의 기울기 |

- **꼭 필요하면 영어를 써도 된다** (예: calculation verification). 한자어보다 영어가 나을 때가 있다.
- 처음 나오는 용어는 **괄호로 한 번 풀어 준다**: "일관접선(수렴용 기울기 행렬)".
- `## 쉬운 설명` 절에서는 전문용어를 아예 쓰지 않는 쪽으로 간다.

### 8) 참고문헌은 **번호를 앞에 붙여** 부른다 (사용자 지정, 2026-08-11)

같은 성(姓)의 저자가 너무 많아 이름만으로는 어느 논문인지 알 수 없다.

```
✅  [12] Skinner 2021 이 ~
✅  [24] Ge 2018 Table 3 에 ~
❌  Skinner 2021 이 ~
```

- `refs/` 에 있는 논문이면 **반드시 `[번호]` 를 앞에 붙인다.**
- `refs/` 에 없으면 번호가 없으므로 그대로 쓰되, **"(refs 미보유)"** 를 한 번 적는다.
- 번호는 `refs/README.md` 의 색인이 정본이다.

### 9) 영어 덩어리는 접어 둔다 (사용자 지정, 2026-08-11)

로그·에러 원문·영문 인용문처럼 **영어가 길게 나오는 것은 펼침으로 감춘다.**

```markdown
<details><summary>원문 (클릭)</summary>

...영어 원문...

</details>
```

- 요약·판정은 **한국어로 밖에** 적고, 영어 원문은 접힌 안쪽에 둔다.
- **굳이 번역해 주지 않아도 된다** — 사용자가 필요하면 펼쳐서 읽는다.
- 명령어·파일명·코드는 영어라도 접지 않는다 (바로 복사해야 하므로).

---

## ★ 자동 체크인은 하루 4번 고정이다 (사용자 지정, 2026-08-12)

a1 우편함(`sync/sync_check.py`)을 보는 자동 체크인은 **한국시각
06:30 · 13:00 · 19:00 · 23:00 네 번만** 돈다. 그 사이에 스스로 깨어나지 않는다.

- 예전에는 1시간(뒤에 2시간) 간격으로 계속 돌았다. 사용자가 **고정 시각**으로 바꿨다.
- 크론은 UTC로 저장된다: `30 21 * * *` 과 `0 4,10,14 * * *`.
- **서버가 발동 시각을 몇 분 뒤로 흩뜨린다**(부하 분산). 실제 발동은 지정 시각
  +5~7분이며 이것은 조절할 수 없다.
- 체크인에서 **변한 것이 없으면 사용자에게 말하지 않는다.** 조용히 끝낸다.
- 체크인 안에서 `send_later` 로 다음 회차를 다시 잡지 않는다 — 크론이 한다.

---

## ★ 두 에이전트 구조 (사용자 지정, 2026-08-05) — **양쪽 세션 공통**

이 논문은 **두 채팅이 각자 브랜치를 갖고** 진행한다.

| | 역할 | 브랜치 | 받는 곳 | 보내는 곳 |
|---|---|---|---|---|
| **에이전트 1** | 논문 조사 · 물성 정리 | `claude/paper-reference-research-pksw5p` | `docs/TO_LITERATURE.md` | `docs/TO_ANALYSIS.md` |
| **에이전트 2** | 코드 작성 · 해석 결과 | `claude/thesis-csic-thermal-shock-5m53iv` | `docs/TO_ANALYSIS.md` | `docs/TO_LITERATURE.md` |

**둘은 서로의 대화를 볼 수 없다. 저장소가 유일한 통신선이다.**

### 반드시 지킬 것 — 세 가지

1. **세션을 시작하면 먼저 돌린다.**
   ```bash
   ```
   브랜치 이름으로 자기 역할을 판단하므로 인자가 필요 없다. 상대가 쌓은 커밋,
   **상대가 내 판정 영역을 건드렸는지**, 내 우편함의 미처리 항목을 보여준다.
   종료코드 1이면 **처리할 것이 있다는 뜻이다.**

2. **커밋하기 전에 한 번 더 돌린다.** 내 변경이 상대의 발견과 어긋나는 채로
   쌓이는 것을 막는다. 실제로 그런 일이 있었다 — 에이전트 2가 얀 $X_t$의
   카드값이 **다발 강도**임을 찾아낸 뒤에도, 에이전트 1은 그것을 모른 채
   "독립 근거 있음"으로 분류한 상태를 유지하고 있었다.

3. **상대에게 알릴 것이 생기면 즉시 발신함에 적는다.** 형식은
   `docs/BRANCH_PROTOCOL.md` §4.4. **처리된 항목은 지우지 말고 ✅ 만 붙인다** —
   왜 그렇게 결정했는지가 나중에 필요해진다.

### 판정이 갈리면

**파일로 영역을 나누지 않는다**(그 규칙은 실패했다). **누가 최종 판정하는가**로 나눈다.

| 사안 | 최종 판정 |
|---|---|
| 값의 **출처·신뢰등급**, **카드 적법성**(구성재 vs 복합재), 장별 **인용** | **에이전트 1** |
| 값을 **코드가 쓰는 방식**, 수렴·솔버·덱·UMAT | **에이전트 2** |

**어느 쪽이든 상대 영역의 파일을 고쳐도 된다.** 단 판정이 갈리면 위 표가 정하고,
**판정권자가 틀렸으면 근거를 가진 쪽 값을 받는다.**

### 병합

- **큰 작업이 끝나면 즉시 병합한다.** 오래 두면 충돌이 커진다.
- 충돌은 대개 **장부 충돌**이다 — 양쪽이 검증 총량 카운터를 다르게 고친 것.
  내용 충돌이면 그것은 **판정이 갈린 것**이므로 위 표로 해결한다.

### ★ 우편함은 `sync/` 다 (a2가 만들고 소유, 2026-08-05)

`sync/PROTOCOL.md`가 정본이다. **`sync/sync_check.py`·`PROTOCOL.md`·`outbox_a2.json`·
`state_a2.json`은 a2 소유이므로 a1은 절대 편집하지 않는다.** 고쳐야 하면
`sync/outbox_a1.json`에 `kind: "question"`으로 요청한다.

```bash
python3 sync/sync_check.py               # a2가 보낸 것 확인
python3 sync/sync_check.py --ack a2-0001 # 반영 완료 기록 ("읽음"이 아니라 "반영함")
```

**a1 소유는 `sync/outbox_a1.json`·`sync/state_a1.json` 둘뿐이다.**

상세는 `docs/BRANCH_PROTOCOL.md`와 `sync/PROTOCOL.md`.

### ★ 제출본은 `docs/CH1~CH7` 이다 (사용자 결정, 2026-08-11)

같은 저장소에 논문 초안이 **두 계보** 있었다 — 이쪽 `docs/CH1~7`(7장, 참고문헌
72건)과 a3 브랜치의 `paper/ch1·ch2·ch4`(3장, 25건). 사용자가 **`docs/`를 제출본**
으로 확정했다. 따라서:

- `paper/`는 **참고 자료**이며 제출본이 아니다. a3의 지적은 받되, 반영 대상은
  `docs/`다.
- `verification/check_manuscript_citations.py` 가 **제출본으로만 범위를 좁힌**
  인용 감사를 돈다. `refs_audit.py`(도서관 감사)와 목적이 다르다 — 후자는
  `docs/` 전체를 훑으므로 **작업 문서에만 등장하는 참고문헌도 통과시킨다.**
  실제로 그 틈에서 [S10] Chaboche 1992가 표에만 있고 어느 장에서도 인용되지
  않은 채 남아 있었다.

### ★ 세 번째 브랜치 — 리뷰 오케스트레이션 a3 (사용자 지정, 2026-08-11)

`claude/llm-task-decomposition-w41jpc` 에서 **4노드 리뷰 파이프라인**이 돈다
(R1 참고문헌 · R2 물성 · R3 수식 · R4 논리 → S 종합). 사용자 지시:
**a3가 보내는 것을 같이 받아서 상의하며 진행한다.**

```bash
python3 verification/review_inbox.py           # 수신·대조 보고
python3 verification/review_inbox.py --check   # 게이트 항목
```

**받을 때 반드시 기억할 것 — a3는 오래된 스냅샷 위에서 돈다.**

- a3에는 **`refs/` 디렉터리가 없다.** 루트에 PDF 3개뿐이고 이쪽은 72개다.
- a3의 초안은 `paper/ch1·ch2·ch4`(Zhang 2022 RVE, 참고문헌 25건)이고
  이쪽은 `docs/CH1~7`(72건)이다. **둘은 다른 문서다.**
- 그래서 a3의 지적은 **둘로 갈라 받는다**: 원문을 봐야 판정되는 것(서지·귀속·
  물성 출처)은 **이쪽이 원문으로 답한다**. 원문이 필요 없는 것(무인용 주장,
  고아 참고문헌, 계산치 대 카드값 혼용, 약속-이행 규율)은 **그대로 유효하며
  `docs/`에도 같은 잣대를 적용한다.**
- **출처 없는 감사는 결함을 만들어내기도 한다.** 실제로 a3 Round 1이
  $G_{f,1c}$의 "Ge Table 3" 귀속을 근거 없다며 "본 연구의 가정"으로 강등했는데,
  Ge Table 3에는 그 값이 실려 있다. **없는 것을 못 찾은 것을 없다고 판정한 것**이며,
  올바른 인용을 지운 쪽이 원래 결함보다 나쁘다. `review_inbox.py`가 이 사례를
  검사로 고정한다.

---

## ★ 해석 실행 원칙 (사용자 지정, 항상 적용)

**Abaqus 해석은 돌리는 데 시간이 오래 걸립니다. 해석 1회에서 최대한 많은 정보를 뽑으세요.**

### 지켜야 할 것

1. **한 잡에서 여러 관측량을 뽑도록 설계한다.**
   - 사이클 사이에 **탄성 프로브 스텝**을 끼워 넣어 `E(N)` 곡선을 한 잡에서 얻는다
     (프로브는 미소 변형 + 사이클률 0 → 손상을 만들지 않음).
   - **체크포인트마다 restart를 기록**해, 잔여강도 시험처럼 시편을 파괴하는 후속 해석을
     별도 잡으로 이어붙일 수 있게 한다. 처음부터 다시 돌리지 않는다.
   - 필드 출력에 **SDV 전체**를 포함한다. 나중에 "그 변수 안 뽑았네"로 재실행하는 것이 가장 큰 낭비.

2. **재사용 가능한 것은 한 번만 계산한다.**
   - 열전달 해석은 TRS 처리 방식과 **무관**하다 → 열충격 심각도 1수준당 **열 잡 1개**를
     계산해 **모든 TRS 케이스가 공유**한다. (3 심각도 × 3 TRS = 9 케이스인데 열 잡은 3개)

3. **작은 선행 검증은 미리 알리고 진행한다.**
   - 큰 매트릭스를 돌리기 전에 반드시 확인해야 하는 것(메시가 열경계층을 푸는지,
     드라이버 전단 순서, cycle jump 오차 등)은 **작은 잡으로 먼저** 확인한다.
   - 단, **무엇을 왜 확인하는지 먼저 말하고** 진행한다. 사용자는 이 방식을 허용했다.

4. **돌리기 전에 덱을 정적 검증한다.**
   - 솔버 없이 가능한 검증(카드 슬롯 수, 가드 상수, 단위, 부호, 파이썬 미러 대조,
     Fortran 크로스체크)을 **전부** 끝낸 뒤에 사용자에게 실행을 요청한다.

### 하지 말 것

- 관측량 하나를 위해 잡 하나를 만드는 것
- 출력 변수를 빠뜨려 재실행하게 만드는 것
- 검증 없이 9-케이스 매트릭스를 통째로 넘기는 것

---

## ★ 해석 파일 전달 규칙 (사용자 지정, 항상 적용)

### 1. zip으로 준다

Abaqus에서 돌려야 할 코드는 **항상 다운로드 가능한 zip 파일**로 전달한다.
개별 파일을 흩어서 주지 않는다. zip 안에는 실행에 필요한 것을 **전부** 넣는다:
입력덱, UMAT 소스, 후처리 스크립트, 그리고 실행 방법을 적은 `RUN_ME.md`.

**폴더를 나누지 않는다. 압축 최상위 폴더 하나 안에 모든 파일을 평평하게 넣는다**
(`src/`, `abaqus/`, `postprocess/` 같은 하위 폴더로 쪼개지 않는다). 사용자가 압축을
풀고 바로 명령어를 실행할 수 있어야 하므로, 파일이 여러 폴더에 흩어져 있으면
`postprocess/extract_ss_curve.py`처럼 경로를 적어줘도 실제로는 그 경로가 없어 실행이
막힌다 (실제로 이 문제로 막힌 적이 있다). 파일명이 겹쳐서 정말 못 합칠 때만
예외로 하되, **먼저 사용자에게 폴더를 나눠도 되는지 물어보고** 진행한다.

### 1-1. ★ 읽을 자료는 **PDF로** 준다 (사용자 지정, 2026-08-04)

문서(목록·보고서·검토서)는 `.md`가 아니라 **PDF로 전달한다.** 사용자가 휴대폰에서
읽고 파일명으로 정리하기 때문이다.

```bash
python3 postprocess/md_to_pdf.py docs/FILE.md --name 최신논문
python3 postprocess/md_to_pdf.py docs/FILE.md --name 최신논문 --stamp 0804_2200
```

- **한글 폰트가 없으면 전부 네모로 나온다.** `fonts-nanum`·`fonts-noto-cjk`가
  필요하며, `--selftest`가 이를 확인한다.
- 변환 후 **`pdftoppm`으로 1페이지를 이미지로 뽑아 눈으로 확인한다.** 첫 시도에서
  인용문 안 목록이 한 문단으로 뭉친 것이 이 확인으로 잡혔다.
- 해석용 zip은 종전대로 zip이다. **PDF는 읽을 자료에만 적용한다.**

### 1-2. ★ 작업 폴더는 `E:\LTH` 다 (사용자·에이전트 합의, 2026-08-07)

**해석 루트는 사용자 워크스테이션의 `E:\LTH\` 이고, 전달 묶음 하나가
그 아래 폴더 하나를 갖는다** (2026-08-07 실사용으로 확정):

```
E:\LTH\LTH_RUN1_0807_1712\LTH_COND_P00.inp
E:\LTH\LTH_RUN1_0807_1712\UMAT_CSIC_THERMSHOCK_V3_0.for
```

즉 사용자는 zip을 `E:\LTH\` 에 그냥 푼다 — 최상위 폴더가 그대로 실행
폴더가 된다. **그 안은 §1대로 평평하다.** 처음에는 파일을 `E:\LTH\` 에
직접 두기로 했으나, 실행할 때마다 `.odb`·`.dat`·`.msg` 가 같은 자리에
쌓여 묶음끼리 섞이므로 **묶음별 폴더가 낫다.**

- **명령을 적을 때 실제 폴더를 전제로 적는다.** 명령창 첫 줄은
  `E:` 다음 `cd \LTH\<묶음이름>` 이고, 그 뒤 명령은 전부 상대 경로로
  쓴다 (그래야 사용자가 그대로 복사해도 안전하다).
- **사용자가 어디에 풀었는지 확인되면 그 경로로 명령을 다시 준다.**
  파일을 옮기라고 하지 않는다 — 이미 푼 것을 다시 만지게 하는 쪽이 실수가 크다.
- 파일명 접두사는 `LTH_` 로 시작해 그 폴더의 것임이 드러나게 한다.
  잡 이름 = 덱 파일 이름 = 후처리가 찾는 이름 — 셋이 항상 같아야 한다.

#### ★ 명령어는 **채팅 본문에** 적는다 (사용자 지정, 2026-08-10)

**해석 파일을 보낼 때는 실행 명령어를 언제나 채팅 답변 안에 같이 적는다.**
`RUN_ME.md` 안에만 두지 않는다. 실제로 그랬고 사용자가 지적했다 — 파일을
받은 사람이 압축을 풀고 문서를 열어야 명령을 찾을 수 있으면 전달이 끝난 것이
아니다. `RUN_ME.md` 는 **사본**이지 정본이 아니다.

지켜야 할 것:

- **경로를 사용자가 실제로 푼 자리에 맞춘다.** 아직 안 풀었으면 내가 정한
  폴더 이름으로 적되, **사용자가 폴더 이름을 바꿔 쓰는 일이 실제로 있으므로**
  (`LTH_RUN2_0807_1830` → `LTH_RUN2_0810_0930`) `cd` 줄 하나만 바꾸면
  나머지는 그대로 돈다는 것을 같이 적는다. 그 뒤 명령은 **전부 상대 경로**다.
- **묶음 이름의 날짜는 만든 날로 적는다.** 사용자는 받은 날짜로 폴더를
  정리하므로, 며칠 지난 이름을 주면 반드시 어긋난다.
- **①실행 · ②완료 후 명령을 둘 다** 채팅에 적는다 (§3-1과 같은 규칙).
- 파일을 보내는 메시지와 **같은 답변 안에** 적는다. "다음 메시지에서
  알려드리겠다" 로 나누지 않는다.

#### ★ 고친 스크립트는 **묻기 전에** 보낸다 (사용자 지정, 2026-08-10)

**사용자가 이미 갖고 있는 파일을 내가 고쳤고 그것을 다시 돌려야 한다면,
고친 파일과 명령어를 그 자리에서 같이 보낸다.** 사용자가 "고친 거 보내줘"
라고 말하게 만들지 않는다. 실제로 그러게 만들었다.

판단 기준은 하나다 — **결함을 보고했다면 고친 것도 같이 간다.**
"다음 답변에서 보내겠다"는 나누기이며 §1-2의 앞 규칙 위반이다.

- 재실행이 **해석까지** 필요한지, **후처리만** 다시 하면 되는지 명시한다.
  후처리만이면 그렇게 말한다 — 사용자가 몇 시간짜리 해석을 다시 돌릴까 봐
  망설이는 것이 가장 큰 손해다.
- **덮어쓸 파일 이름과 폴더를 정확히 적는다.**
- 고친 것이 여러 개면 zip, 하나면 파일 하나로 보낸다 (§1의 zip 규칙은
  **해석 묶음**에 대한 것이고, 교체 파일 한 개까지 zip으로 싸지 않는다).

---

### 2. 파일명에 날짜·시각을 붙인다

형식: **`파일명_MMDD_HHMM`** — 한국 시각(KST) 기준.

```
예) 7월 28일 오후 3시 36분  ->  M1_ZHANG2022_0728_1536.zip
```

생성 시각은 만들 때마다 확인한다:

```bash
TZ=Asia/Seoul date "+%m%d_%H%M"
```

### 3. 병렬로 돌릴 수 있으면 그렇게 알려준다

잡들 사이에 의존성이 없으면 — 즉 A의 결과가 B의 입력이 아니면 — **순차로 시키지 않는다.**
다음과 같이 명시한다:

> **Abaqus Command 창을 3개 열고 각각 하나씩 입력하세요.**

그리고 **각 창에 넣을 명령어를 그대로 하나씩** 적어 준다. 사용자가 조합하게 만들지 않는다.

의존성이 있으면 그것도 명시한다. 예:
- 열전달 잡 → 역학 잡 (역학이 열 ODB를 읽음): **순차**
- 같은 심각도의 TRS A/B/C 역학 잡: **서로 독립 → 병렬**
- restart 이어받는 잔여강도 잡: 부모 역학 잡 **이후**

### 3-1. ★ 실행 명령과 **완료 후 명령**을 항상 같이 준다 (사용자 지정)

Abaqus는 `.odb`만 만든다. **CSV·그림은 저절로 나오지 않는다.**
따라서 명령을 줄 때는 **반드시 두 묶음**으로 준다:

```
① 해석 실행 명령      (abaqus job=... )
② 해석 완료 후 명령    (abaqus python ...  → csv,  python3 ... → 그림)
```

②를 빠뜨리면 사용자가 해석을 다 돌리고 나서 "이제 뭘 해야 하냐"고 다시 물어야 한다.
실제로 한 번 그랬다. **한쪽만 주지 않는다.**

지켜야 할 것:
- **잡 이름과 후처리 파일 이름을 일치시킨다.** 후처리 스크립트는 `<잡이름>.odb`를
  읽고 `<잡이름>_ss.csv`를 쓴다. RUN_ME.md의 예시 잡 이름과 채팅에서 준 잡 이름이
  다르면 사용자가 그대로 복사했을 때 파일을 못 찾는다. (이 실수도 실제로 났다)
- **`abaqus python`인지 `python3`인지 명시한다.** ODB를 읽는 스크립트는
  `odbAccess`가 필요하므로 **반드시 `abaqus python`**. 그림 그리는 스크립트는
  matplotlib가 필요하므로 **일반 `python3`**. 둘을 바꿔 쓰면 즉시 에러.
- **후처리에는 `cpus`/`memory`를 붙이지 않는다.** 단일 스레드 · 수 초짜리다.
- **잡 하나가 끝날 때마다 바로 돌릴 수 있다고 알려준다.** 3개를 다 기다릴 필요 없다.

### 3-2. ★ 결과는 **CSV로 뽑고 그 파일을 주고받는다** (사용자 지정, 2026-08-07)

**후처리 스크립트는 콘솔 출력만 하고 끝내지 않는다. 반드시 CSV를 쓴다.**
사용자는 그 CSV를 채팅에 올리고, 나는 그것을 읽는다.

왜 이 규칙이 생겼나 — 2026-08-07 `extract_kbar` 결과를 **화면 캡처**로 받았다.
읽히기는 했지만 그 방식은 세 가지가 나쁘다:

1. **숫자를 다시 타이핑해야 한다.** 이 프로젝트가 계속 잡아온 사고가 전사
   오류다(Snead 부호, Pradère 단위, [28] 페이지 절단).
2. **잘린다.** 캡처는 창 크기에서 끝나고, 잘린 자리가 하필 판정줄일 수 있다.
3. **재계산이 안 된다.** CSV면 내가 그 자리에서 상한·비율을 다시 셀 수 있다.

지켜야 할 것:

- **후처리 스크립트는 `<무엇>_summary.csv` 를 무조건 쓴다.** 판정이 실패했을
  때도 쓴다 — 어느 행을 버려야 하는지가 그 파일에 있어야 한다.
- **CSV에는 판정에 쓴 근거를 같은 행에 담는다.** 값만 담지 않는다.
  예: `kbar1, voigt_inplane, kbar1_admissible` 처럼 **값·기준·판정**이 나란히
  있어야 사용자도 나도 다시 확인할 수 있다.
- **`RUN_ME.md`에 "이 CSV를 채팅에 올려 주세요"를 명시한다.** 어떤 파일인지
  이름으로 적는다.
- 콘솔 출력은 **없애지 않는다.** 사람이 그 자리에서 읽는 로그로 남기되,
  **전달물은 CSV다.**

---

### 4. 사용자 워크스테이션 사양에 맞춰 명령을 낸다

**사용자 실행 환경: CPU 32코어 / RAM 256 GB.**

명령을 적을 때 `cpus`와 `memory`를 **항상 명시**한다. 기본값에 맡기지 않는다.

#### 코어 배분 원칙

Abaqus/Standard(음해법)는 코어 수에 **선형으로 빨라지지 않는다**(8코어 넘어가면
효율이 뚝 떨어짐). 반면 **독립 잡을 동시에 돌리면 처리량은 거의 선형**이다.
따라서 **잡 1개에 32코어를 몰아주지 말고, 독립 잡들에 나눠준다.**

| 동시 실행 잡 수 | 잡당 `cpus` | 합계 | 잡당 `memory` |
|---|---|---|---|
| 1 | 16 | 16 | `"180gb"` |
| **3** | **10** | **30** | **`"70gb"`** |
| 4 | 8 | 32 | `"55gb"` |
| 9 (전체 매트릭스) | 3 | 27 | `"25gb"` |

- OS 여유로 **2코어는 남긴다** (32 전부 쓰지 않는다).
- **`memory`를 반드시 명시한다.** Abaqus 기본값은 물리 메모리의 90 %라서,
  잡 3개를 동시에 띄우면 **서로 메모리를 뺏다가 스와핑으로 오히려 느려진다.**
  합계가 200 GB를 넘지 않게 잡는다.
- 라이선스 토큰은 `int(5 · cpus^0.422)` 로 늘어난다 (10코어 ≈ 13토큰).
  **토큰이 모자라면 `cpus`를 줄인다** — 잡 수를 줄이지 않는다.

#### 명령 형식 (이대로 적어 준다)

```
abaqus job=<잡이름> input=<덱> user=<UMAT> double interactive cpus=10 memory="70gb"
```

- `double` — **필수**. 단정밀도면 손상 적분이 깨진다.
- `interactive` — 진행 확인용. 백그라운드로 돌릴 땐 뺀다.
- 스크래치 디스크가 SSD면 `scratch=<경로>` 를 추가 권장.

### 5. 외부 의존 파일을 반드시 확인하고 알린다

`.inp`가 `Input=...` 으로 외부 파일(예: TexGen `.ori` 방향 파일)을 참조하면,
zip에 넣거나 **넣을 수 없으면 사용자에게 어떤 파일을 어디에 두어야 하는지 명시**한다.
빠지면 잡이 즉시 죽는다.

---

## 메시 전략 (사용자 결정)

**탐색 단계는 거친 RVE 메시(2~4만 요소)로 빠르게 돌리고, 정밀도가 필요해지는 시점에
메시 수렴성 검증을 한다.** 상세는 `docs/MESH_STRATEGY.md`.

지켜야 할 것:
- **`.ori`는 메시와 한 몸이다.** 메시를 새로 뽑으면 `.ori`도 반드시 새로 뽑는다.
  옛 `.ori`를 새 메시에 쓰면 **에러 없이 섬유 방향이 틀린 채로 수렴한다.**
- 거친 메시로도 **C̄, ᾱ, k̄ 는 거의 최종값**이다 (체적 평균이라 빨리 수렴).
  **강도 X̄·Ȳ·S̄ 와 손상 분포는 메시 민감**하므로 수렴성 검증 후에 확정한다.
- 새 덱을 만들 때 `assemble_inp.py --inline-ori` 를 쓰면 `.ori`가 덱 안에 들어가
  **자기완결**이 된다. zip 전달 시 파일 누락이 원천 차단되므로 거친 메시에는 항상 쓴다.
- 거시 열충격 메시는 **RVE와 무관하게** 별도로 정한다 (열경계층 분해가 제약).

---

## 코드 규칙

- **V1_0 UMAT(`src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for`)은 동결.** Zhang 2022 검증이 걸려 있다.
  기능 추가는 `src/UMAT_CSIC_THERMSHOCK_V3_0.for`(V3_0 계보)에서 한다.
- V3_0은 V1_0의 **엄격한 상위집합**이어야 한다. 회귀 테스트(T2)가 이를 강제한다.
- 물성 숫자는 CSV에 손으로 적지 말고 **`data/properties/eval_correlations.py`에 상관식으로**
  넣는다. 전사 오류가 두 번 나왔다(Snead 마이너스 부호, Pradère 단위).
- 문헌 데이터는 **신뢰도 등급**(`fulltext`/`digitized`/`abstract`/`secondary`)을 반드시 붙인다.
  `secondary`는 논문 인용 금지.
- **구성재 데이터만 카드 입력.** 복합재 측정값은 검증 전용 — 섞으면 TRS를 이중 계산한다.

## 검증 명령

```bash
bash verification/compile_check.sh              # 두 UMAT 컴파일
python3 verification/verify_constitutive.py     # V1_0 수식
python3 verification/micromech_check.py         # 얀 물성
python3 verification/verify_thermshock.py       # V3_0 기능 + 보정
python3 verification/cross_check_fortran.py     # 컴파일된 Fortran vs Python
python3 data/properties/eval_correlations.py --check
python3 abaqus/build_temperature_tables.py --selftest
python3 abaqus/make_macro_thermalshock.py --selftest   # 거시 카드 정적 검증
python3 data/properties/conductivity_bounds.py --check # 열전도 경계·민감도
python3 data/properties/conductivity_temperature.py --check # k(T) 형상 유도 (차용 기각)
python3 data/properties/yarn_fracture_energy.py --check # 얀 횡방향 Gtt/Gtc 출처 + 균열대 적합성
python3 data/properties/cte_sensitivity.py --check     # 구성재 CTE가 TRS 2.34배에 미치는 몫
python3 data/properties/trs_configuration.py --check   # CONFIG_V / CONFIG_P 결정
python3 data/properties/card_gap_triage.py --check    # GUESS 14개 knob/도출/공백 분류
python3 data/properties/m6_calibration.py --check      # M6 보정 knob 우선순위
python3 data/properties/insitu_yarn_strength.py --check # 얀 Xt in-situ 출처·Weibull 구간
python3 data/properties/porosity_stiffness.py --check  # 공극률 결정 + 강성 정합
python3 data/properties/make_property_workbook.py --check # 물성 현황표(엑셀) 생성기
python3 postprocess/msg_residual_census.py --check     # .msg 잔차가 어느 상에 있나
python3 abaqus/make_rve_conductivity.py --check        # RVE 열전도 덱 (면집합·DC3D4)
python3 data/literature/digitize.py --check           # 그림 디지타이즈 재현
python3 data/literature/zhang5_provenance.py --check   # Zhang[5] 밀도·공극률 진술 유무 + 기지 E 정합
python3 data/literature/refs_audit.py --check          # refs/ 전수 점검 (중복·고분자기지·인용누락)
python3 data/literature/gf_temperature.py --check      # Gf(T) 방향 출처 + A 표류 한계
python3 data/literature/pls_validation.py --check      # 비례한도를 TRS 검증 지표로
python3 data/literature/cte_composite_targets.py --check # 복합재 CTE 절대 표적 4점
python3 data/literature/cte_rve_verdict.py --check    # RVE 실물 CTE 대 절대 표적 (4단 사다리)
python3 data/literature/modulus_definition.py --check  # 대조 모듈러스 정의 (접선 vs 할선)
python3 data/literature/crack_band_simplex.py --check   # refs/[47]의 2D 사면체 배수 (a2 kappa 검증)
python3 data/literature/thermal_cycling_dataset.py --check # 반복 열충격 전 데이터 + 심각도 역설
python3 data/literature/cycle_jump_provenance.py --check # cycle jump 기준 출처 [57]/[58]
python3 data/literature/digitize_ref28_fig17.py --check # refs/[28] Fig.17 TRS (Table 1로 검산)
python3 data/literature/cte_r11_envelope.py --check    # refs/[11] 복합재 CTE가 판정선이 되는지
python3 abaqus/quench_calibration.py --check          # 급랭 h 보정 + Biot
python3 abaqus/retune_deck.py --check                 # 덱 재튜닝 (카드 슬롯 + 스텝)
python3 verification/check_ch1_numbers.py             # Ch.1 인용·기여·전방참조 (검증 1회차)
python3 verification/check_ch2_numbers.py             # Ch.2 본문 수치 vs 문헌 CSV
python3 verification/check_ch3_numbers.py             # Ch.3 검증 개수 vs 실제 (느림)
python3 verification/check_ch4_numbers.py             # Ch.4 수치 vs 1차 출처 (검증 1회차)
python3 verification/check_ch5_numbers.py             # Ch.5 vs 덱 생성기 실제값 (검증 1회차)
python3 verification/check_ch6_numbers.py             # Ch.6 검증표적 vs 사이클 데이터셋 (검증 1회차)
python3 verification/check_ch7_numbers.py             # Ch.7 결론 경계 — 결과 없는 결론만 (검증 1회차)
python3 verification/check_chapter_consistency.py     # 장 간 모순 (검증 2회차)
python3 verification/check_chapter_claims.py          # 장이 부른 파일·명령 (검증 3회차, 느림)
python3 verification/check_chapter_flow.py            # 1~5장 유기적 연결성 (검증 4회차)
python3 verification/review_inbox.py --check           # 리뷰 브랜치 수신·원문 대조 (a3)
python3 verification/check_manuscript_citations.py     # 제출본(CH1~7) 인용 전수 (고아·허공·무인용 주장)
python3 verification/prerun_gate.py --check            # 최소 해석 계획·단계별 관문 (a1 몫)
python3 verification/pending_slots.py --check          # [결과 대기] 슬롯 8개 — 단계·소유자·차단/부분
python3 verification/check_card_ranges.py             # 카드 입력 vs 독립 문헌 범위 (실행 전 관문)
python3 verification/check_gf_scale_transfer.py        # Gbar_f가 RVE 크기를 달고 넘어가는지 (M6 관문)
python3 verification/m6_calibration_plan.py            # M6가 무엇을 움직이고 무엇을 건드리면 안 되는지
python3 verification/plastic_dissipation_audit.py      # Ge (23)(24) 소성분이 A_m에 들어가는가 (철회 기록)
python3 verification/reheat_saturation.py --check      # 재가열 상한 도달의 원인 (점성 지연 16 % + 재분배 84 %)
python3 verification/knob_sensitivity.py --check       # knob→관측량 정량 자코비안 + SVD 식별성 (rF 파생)
python3 postprocess/m6_report.py --selftest            # M6 결과 판독기 (피크 + 냉각 후 접선)
python3 postprocess/m6_verdict.py --selftest          # M6 판정기 (접선 정의 단일화 + CSV)
python3 postprocess/compare_tangent.py --selftest      # ITAN 0/1 수렴 비용 대조 (.msg)
python3 postprocess/md_to_pdf.py --selftest            # 문서 PDF 변환 (한글 폰트 + 파일명 규칙)
python3 postprocess/md_to_docx.py --selftest           # 논문 초안 워드(.docx) 합본 생성기
python3 postprocess/make_thesis_figures.py --check      # 논문 그림 생성기 (문헌값 재유도 + 본문 삽입)
python3 abaqus/make_patch_tests.py --check            # 패치·균열대 덱 (Jacobian 포함)
python3 postprocess/extract_kbar.py --selftest        # kbar 공극률 판정 산식
python3 postprocess/extract_pls.py --selftest         # 비례한도(PLS) 추출 정의 4종
python3 postprocess/extract_probe.py --selftest       # E(N) 프로브 판독 산식
python3 postprocess/compare_cyclejump.py --selftest   # cycle-jump 오차 판정 규칙
python3 postprocess/damage_map.py --selftest           # 손상 지도 (상 통일 DAMG + 최악부 CSV)
python3 postprocess/damage_census.py --check           # 손상 census (ATEFF 클램프 비율 = 강도 인용 관문)
python3 postprocess/damage_ceiling.py --selftest       # 손상 상한 0.9 판정 (어디·언제·얼마나 + 판정 불가 선언)
python3 postprocess/extract_thermal_profile.py --selftest # 급랭 구배가 메시·증분·카드로 풀렸나
python3 postprocess/homogenize.py --selftest           # 거시 카드 조립 (드라이버→히스토리 해결)
python3 verification/celent_census.py                 # le=CELENT의 파괴에너지 오차
python3 sync/sync_check.py --selftest                 # 두 에이전트 우편함 규약
python3 sync/sync_check.py                            # ★ 상대 브랜치 새 메시지 (네트워크)
```

**커밋 전에 위 70개를 전부 통과시킨다.**

> `sync/sync_check.py`(인자 없음)는 **상대 에이전트 브랜치를 fetch** 한다.
> `blocking` 메시지가 미처리면 **exit 1** 이므로 커밋이 막힌다 — 이것이
> "상대가 갱신하면 알아차린다"의 실제 구현이다. 규약은 `sync/PROTOCOL.md`.

## 현재 병목

**M1** — Zhang Table 3(128.45 / 179.42 / 199.15 MPa)에 맞춘 보정.
1차 `ZHANG2022_c26k_*`(0728) 전멸 → 2차 `M1FIX_c26k_*`(0729) 전멸 →
3차 `M3_c26k_*`(0730): **z600 완주**, RT23 98.2 %, T500 67.3 %, T1000 57.2 %.
재가열 스텝은 $H_{smo}$=0.1로 **완전히 해결**되었다(실패 시도 0회).
남은 병목은 인장 스텝의 **자유 매크로 드라이버**이며, 4차는 `M4_c26k_*`.
전말은 `docs/M1_FAILURE_ANALYSIS.md` Round 4.

M1에서 나온 교훈 — 다음 덱에도 계속 적용한다:

- **비수렴을 절점 탓으로 돌리기 전에 그 절점 번호를 덱에서 찾아본다.**
  Round 3에서 5681–5686을 메시 절점으로 착각해 "두께 방향(자유도 3)이 원인"이라는
  잘못된 결론을 냈다. 실제로는 주기경계조건 **더미 드라이버 절점**이고, 그 "자유도 1"은
  전역 x가 아니라 그 드라이버의 유일한 자유도였다.
- **자유(하중 없는) 드라이버의 잔차는 곧 매크로 응력 오차다** — $R = \sigma V_{RVE}$.
  절대 응력으로 환산해 보고 판단한다. M3에서 그 값은 1e-2 MPa 이하였는데
  Abaqus는 1.4e-4 MPa를 요구하고 있었다.

- **죽은 잡의 `.odb`도 냉각 스텝은 온전하다.** 새로 돌리기 전에
  `postprocess/damage_census.py`로 먼저 읽는다. 공짜다.
- **비수렴이 시간증분 문제인지 먼저 확인한다.** 변위 증분이 1e-9까지
  줄었는데도 안 붙으면 증분 크기 문제가 아니다. 컷백을 더 허용해도 소용없다.
  최소 증분은 1e-8 이하로 내리지 않는다(죽는 데만 20분 넘게 쓴다).
- **`*Static, stabilize=`를 쓰면 `ALLSD/ALLIE`를 반드시 같이 출력하고
  5 % 미만인지 확인한다.** 안 하면 피크 응력이 인공 감쇠로 부풀려진 채
  논문에 들어간다.
- **응력자유온도(`*Expansion, zero=`)는 물성 가정이지 솔버 설정이 아니다.**
  수치 수정과 절대 같은 덱에 섞지 않는다.
