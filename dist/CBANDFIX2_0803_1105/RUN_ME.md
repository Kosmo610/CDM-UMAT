# cband_damage.py 2차 수정 — 원인 확정됨

진단 출력이 답을 줬습니다. 덱의 `*Depvar`가 **이름을 함께 주기 때문에**
Abaqus가 `SDV1`이 아니라 **`SDV_DMT`** 로 씁니다.

```
*Depvar
20,
1, DMT, Matrix tensile damage      <-- 이 이름이 SDV_DMT 가 된다
```

이제 **이름을 먼저** 찾고, 없으면 번호(`SDV1`), 그것도 없으면 성분을 가진 `SDV`를
찾습니다.

```
abaqus python cband_damage.py CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb > cband_damage3.txt
```

## 봐야 할 것

- **`rows`** — 손상된 요소 열의 개수. **셋 다 1이어야** 균열대 이론의 전제가 성립합니다.
  메시마다 다르면 소산에너지 비교 자체가 무의미해집니다.
- **`sat?`** — `d_max`가 카드 상한 0.90에 닿았는지. 일부만 YES면 세 봉이 다른 단계입니다.
