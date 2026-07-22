# 메쉬 재생성 → 조립 워크플로우 (coarse mesh로 경향 먼저 확인)

목적: 논문 메쉬(174,405 C3D4)로 바로 가지 말고, 먼저 **2~4만 요소**의 성긴 메쉬로
경향(냉각 손상, 온도별 강도 추세)을 빠르게 확인한 뒤, 같은 절차로 다시 조밀 메쉬를
돌려 논문 수치에 맞춰가는 전략입니다. 크랙밴드 정규화 덕분에 메쉬가 바뀌어도 재료
카드·스텝은 그대로 재사용됩니다.

## 1. TexGen에서 성긴 메쉬 생성 (사용자 작업)

- 기존과 **동일한 평직 RVE**(3.5 × 3.5 × 0.4334 mm, Vf≈40%)를 열고, 메쉬 밀도(voxel
  해상도 / tet seed size)만 키워서 요소 수를 **20k~40k**로 낮춥니다.
  - 요소 수는 선형 해상도의 세제곱에 비례 → 174k에서 ~30k로 줄이려면 선형 seed를
    대략 **1.8배 성기게** (voxel 해상도를 약 55%로) 설정하면 근처에 옵니다. 한 번
    뽑아보고 요소 수 보고 조정하세요.
- **Abaqus(.inp)로 export** 하되, 기존 파일과 같은 옵션을 쓰세요:
  - Periodic BC(주기경계, Xia 방식) 포함 → `ConstraintsDriver0..5`, `FaceA..F`,
    `*Equation` 이 생성되어야 함
  - Material orientation(섬유 방향) 포함 → `*Orientation` + `.ori` 파일 생성
  - ElSet 이름: `Matrix`, `Yarn0..YarnN` (TexGen 기본)
- 결과물: `coarse_mesh.inp` **와** 함께 나오는 `*.ori` 파일. **둘 다** 보관하세요
  (.ori는 요소별 섬유방향 데이터라 메쉬마다 새로 생성됩니다).

> TexGen이 재료/스텝을 자동으로 넣더라도 상관없습니다. 조립 스크립트가 그 부분은
> 버리고 올바른 UMAT 카드/스텝으로 교체합니다.

## 2. 조립: 재료카드 + 3스텝 붙이기 (스크립트)

```bash
python3 assemble_inp.py  coarse_mesh.inp  --model v2  --prefix ZHANG2022_coarse
#   -> ZHANG2022_coarse_RT23.inp, _T500.inp, _T1000.inp
```

- `--model v2` : 풀 모델(소성+Eq.18 ON). 경향 확인용으로 먼저 `--model v1`(탄성손상
  기저, 더 안정적)로 돌려보는 것도 권장.
- `--only RT23` : 한 온도만 조립(23℃부터 빠르게 확인할 때).
- 스크립트가 메쉬에서 yarn ElSet 개수·orientation 이름·노드 범위를 자동 감지하므로
  요소 수가 달라도 그대로 동작합니다.

## 3. 실행 (사용자 Abaqus)

`.inp`, `.ori`, UMAT `.for` 를 **한 폴더**에 두고:

```bash
abaqus job=Job_coarse_RT23 input=ZHANG2022_coarse_RT23.inp \
       user=../src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
```

성긴 메쉬라 빠르게 끝납니다. 먼저 23℃ 하나로 (a) 수렴하는지, (b) 냉각 후 매트릭스
손상이 광범위(SDV로 DMT/DMACT 확인)한지, (c) 인장 곡선이 나오는지 확인하세요.

## 4. 경향 확인 → 조밀화

```bash
abaqus python ../postprocess/extract_ss_curve.py Job_coarse_RT23.odb
python3 ../postprocess/plot_compare.py Job_coarse_*_ss.csv
```

성긴 메쉬에서 **온도 올라갈수록 강도 증가** 경향과 곡선 모양이 논문과 비슷하게
나오면, 같은 `assemble_inp.py`를 **조밀 메쉬**(TexGen에서 다시 뽑은 100k+ 요소)에
적용해 수치를 맞춰갑니다. 보정 파라미터 튜닝은 `../verification/CALIBRATION_GUIDE.md`.

## 전제 / 주의

- TexGen export는 **flat 모델**(`*Part`/`*Assembly` 없이 노드/요소 직접 정의)이어야
  합니다. 현재 V1_0/V2_0 파일이 그 형식입니다. Assembly 형식으로 나오면 알려주세요.
- 재료 이름은 UMAT의 CMNAME 검사 때문에 반드시 `SIC_MATRIX_DAMAGE`(‘MATRIX’ 포함),
  `CSIC_YARN_DAMAGE`(‘YARN’ 포함)로 붙습니다(스크립트가 자동).
- 실행은 반드시 **double precision**(`abaqus ... double`).
- 성긴 메쉬는 경향 확인용입니다 — 절대 강도는 조밀 메쉬에서 수렴시켜 논문과 비교하세요.
