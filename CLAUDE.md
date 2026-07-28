# CDM-UMAT — 작업 규칙

석사학위논문 프로젝트. 개요는 `README.md`, 연구계획은 `docs/THESIS_PLAN.md`,
노벨티는 `docs/NOVELTY.md`.

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
```

**커밋 전에 위 7개를 전부 통과시킨다.**

## 현재 병목

**M1** — 사용자 PC의 Abaqus로 기존 `abaqus/ZHANG2022_*_V2_0.inp` 3케이스를 실행하고
Zhang Table 3(128.45 / 179.42 / 199.15 MPa)에 맞춰 보정. 이 결과 없이 그 위를 쌓으면
잘못된 물성 위에 논문을 짓게 된다.
