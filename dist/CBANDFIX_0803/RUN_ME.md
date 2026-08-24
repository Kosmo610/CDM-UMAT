# cband_damage.py 수정본

전에는 `SDV1`이라는 이름만 찾았고, 없으면 그냥 포기했습니다. 이제:

1. `SDV1`, `SDV_1`, `SDV01`, 그리고 성분을 가진 단일 `SDV`까지 **모두 시도**합니다.
2. 필드 출력이 실제로 있는 **마지막 프레임**을 찾아 씁니다(마지막 프레임이 비어 있을 수 있음).
3. 그래도 못 찾으면 **그 프레임에 실제로 있는 변수 이름을 전부 찍습니다.**

```
abaqus python cband_damage.py CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb > cband_damage2.txt
```

이번엔 답이 나오거나, **왜 안 나오는지가 나옵니다.** 둘 중 하나입니다.
