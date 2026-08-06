const pptxgen = require("pptxgenjs");

// ---------- palette (same language as the full deck) ----------
const INK        = "1A1D21";
const GRAPHITE   = "24282E";
const PAPER      = "FFFFFF";
const TINT       = "F1F2F4";
const EMBER      = "D9542B";
const EMBER_SOFT = "FAE7DF";
const STEEL      = "3F6B7D";
const STEEL_SOFT = "E3ECF0";
const MUTED      = "6E7681";
const ICE        = "C6CDD5";
const GREEN      = "2F6B4F";
const GREEN_SOFT = "E2EEE8";
const AMBER      = "9C6B10";

const KF = "맑은 고딕";
const MONO = "Courier New";
const M = 0.62;
const CW = 13.333 - 2 * M;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "C/SiC RVE — 조립 · 주기경계조건 · 검증 (4장)";

function sl() { const s = pres.addSlide(); s.background = { color: PAPER }; return s; }
function head(s, eyebrow, title, ts) {
  s.addText(eyebrow, { x: M, y: 0.30, w: CW, h: 0.24, fontFace: KF, fontSize: 11, bold: true, color: EMBER, charSpacing: 1.4, margin: 0 });
  s.addText(title, { x: M, y: 0.58, w: CW, h: 0.62, fontFace: KF, fontSize: ts || 27, bold: true, color: INK, margin: 0, valign: "top" });
}
function foot(s, text) {
  s.addText(text, { x: M, y: 6.98, w: CW, h: 0.28, fontFace: KF, fontSize: 9, color: MUTED, margin: 0, valign: "middle" });
}
function card(s, x, y, w, h, fill, line) {
  const o = { x, y, w, h, fill: { color: fill }, rectRadius: 0.06 };
  if (line) o.line = { color: line, width: 1 };
  s.addShape(pres.ShapeType.roundRect, o);
}
function chip(s, n, x, y, color, d) {
  d = d || 0.36;
  s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color } });
  s.addText(String(n), { x, y, w: d, h: d, align: "center", valign: "middle", margin: 0, fontFace: KF, fontSize: 12, bold: true, color: PAPER });
}

// =====================================================================
// 1. RVE -> full analysis model (materials + orientation into every element)
// =====================================================================
{
  const s = sl();
  head(s, "MODEL ASSEMBLY", "RVE → 해석 모델 — 요소 174,405개 전부에 재료와 방향을 넣는다", 24);

  // left: 3-step flow
  const flow = [
    ["TexGen 출력 3종 세트", ".inp 메쉬 + 주기경계 · .ori 요소별 섬유방향 · .eld 요소별 얀 정보", EMBER],
    ["assemble_inp.py 로 조립", "TexGen 이 붙인 재료·스텝은 버리고 UMAT 카드로 교체 · 얀 물성은 Chamis/Schapery 균질화 (오차 0.005 % 이내)", STEEL],
    ["3온도 해석 덱", "RT23 / T500 / T1000 · double precision 필수 · 메쉬가 바뀌어도 카드·스텝은 재사용 (크랙밴드 정규화)", GREEN],
  ];
  let fy = 1.52;
  flow.forEach((f, i) => {
    card(s, M, fy, 6.30, 1.14, TINT);
    chip(s, i + 1, M + 0.22, fy + 0.20, f[2], 0.38);
    s.addText(f[0], { x: M + 0.76, y: fy + 0.10, w: 5.3, h: 0.32, fontFace: KF, fontSize: 12.5, bold: true, color: INK, margin: 0 });
    s.addText(f[1], { x: M + 0.76, y: fy + 0.44, w: 5.34, h: 0.64, fontFace: KF, fontSize: 10, color: MUTED, margin: 0, lineSpacingMultiple: 1.15 });
    if (i < 2) s.addText("▼", { x: M + 2.9, y: fy + 1.14, w: 0.4, h: 0.24, fontFace: KF, fontSize: 10, color: "AEB4BC", align: "center", valign: "middle", margin: 0 });
    fy += 1.38;
  });

  // right: what goes into every element
  card(s, 7.20, 1.52, 5.50, 4.10, GRAPHITE);
  s.addText("요소마다 들어가는 것", { x: 7.46, y: 1.70, w: 5.0, h: 0.30, fontFace: KF, fontSize: 13, bold: true, color: EMBER, margin: 0 });
  const rows = [
    ["상(相) 배정", "기지 91,554 · 얀(Yarn0–3) 82,851 = 174,405 C3D4 — ElSet 로 전 요소 분류"],
    ["섬유 방향", ".ori 요소별 방향 2벡터 — warp ∥ x · weft ∥ y, 얀 굴곡(crimp)까지 반영"],
    ["재료 카드", "SIC_MATRIX_DAMAGE / CSIC_YARN_DAMAGE — UMAT 이 CMNAME 으로 구분"],
    ["체적분율", "얀 50.51 % × 얀 내부 Vf 0.792 = 전체 Vf 0.4000 — 논문 40 % 일치"],
  ];
  let ry = 2.10;
  rows.forEach((r) => {
    s.addText(r[0], { x: 7.46, y: ry, w: 1.30, h: 0.72, fontFace: KF, fontSize: 10.5, bold: true, color: ICE, valign: "top", margin: 0 });
    s.addText(r[1], { x: 8.82, y: ry, w: 3.66, h: 0.72, fontFace: KF, fontSize: 10.5, color: PAPER, valign: "top", margin: 0, lineSpacingMultiple: 1.15 });
    ry += 0.80;
  });
  s.addText("주의 — .ori 는 메쉬와 한 몸. 새 메쉬에 옛 .ori 를 쓰면 에러 없이 방향이 틀린 채 수렴한다.", {
    x: 7.46, y: 5.26, w: 5.0, h: 0.30, fontFace: KF, fontSize: 9.5, color: "F0B27A", margin: 0,
  });

  // bottom strip: analysis steps
  card(s, M, 5.86, CW, 0.94, STEEL_SOFT);
  s.addText([
    { text: "해석 스텝  ", options: { bold: true, color: STEEL, fontSize: 12 } },
    { text: "Step 1 냉각 1050 → 23 °C   →   Step 2 승온 23 °C → 시험온도   →   Step 3 인장 (x 방향)   ", options: { color: INK, fontSize: 12 } },
    { text: "+ HOM 섭동 6스텝 (논문에 없음 — 손상 후 강성 6×6 추출용)", options: { color: MUTED, fontSize: 10.5 } },
  ], { x: M + 0.28, y: 5.86, w: CW - 0.56, h: 0.94, fontFace: KF, margin: 0, valign: "middle" });

  foot(s, "출처 — abaqus/assemble_inp.py · abaqus/meshes/README.md · PAPER_DEVIATION_REGISTER §5.8 (요소수) · check_pbc.py (상 분율, 174,405 생산 덱 기준) · 논문 §3.2.4");
  s.addNotes("TexGen 형상(앞 슬라이드)에서 나온 메쉬를 해석 모델로 만드는 단계입니다. 핵심: 요소 하나하나가 상·방향·재료카드를 받고, 전체 Vf 0.4000이 논문과 일치함을 확인했습니다.");
}

// =====================================================================
// 2. PBC application
// =====================================================================
{
  const s = sl();
  head(s, "PBC — HOW", "주기경계조건 적용 — *Equation 57식 + 드라이버 절점 6개", 25);

  card(s, M, 1.50, CW, 0.70, EMBER_SOFT);
  s.addText([
    { text: "왜 — ", options: { bold: true, color: EMBER } },
    { text: "시편 게이지부(30 × 6 × 3.5 mm)에는 단위셀이 ≈ 119개(치수로부터 계산). 하나만 모델링하고, 마주보는 면을 묶어 무한 반복 매질로 만든다.", options: { color: INK } },
  ], { x: M + 0.28, y: 1.50, w: CW - 0.56, h: 0.70, fontFace: KF, fontSize: 12, margin: 0, valign: "middle" });

  // left: constraint equations
  card(s, M, 2.42, 6.30, 3.98, GRAPHITE);
  s.addText("구속식 (Xia 형식 — TexGen 생성)", { x: M + 0.30, y: 2.60, w: 5.7, h: 0.28, fontFace: KF, fontSize: 11.5, bold: true, color: EMBER, margin: 0 });
  s.addText("u_slave - u_master = H . d\n\nH = [ e_x   e_xy  e_xz ]\n    [  0    e_y   e_yz ]\n    [  0     0    e_z  ]\n\nFaceA - FaceB - Lx . U_d0 = 0", {
    x: M + 0.30, y: 2.94, w: 5.7, h: 2.30, fontFace: MONO, fontSize: 12.5, color: PAPER, margin: 0, lineSpacingMultiple: 1.18,
  });
  s.addText("→ 드라이버 절점의 변위 U 가 곧 거시 변형률 그 자체", {
    x: M + 0.30, y: 5.44, w: 5.7, h: 0.34, fontFace: KF, fontSize: 12, bold: true, color: "F0B27A", margin: 0, valign: "middle",
  });

  // right: 4 mechanics
  const items = [
    ["*Equation 57 식", "마주보는 면의 절점쌍을 격자벡터 하나만큼 묶는다. 나열 순서가 곧 짝짓기 — 세트를 정렬하면 깨진다 (TexGen 의 Unsorted)"],
    ["드라이버 절점 6개", "요소에 물리지 않은 순수 DOF 운반체 — 0=e_x 1=e_y 2=e_z 3=e_xy 4=e_xz 5=e_yz 를 직접 구동"],
    ["코너 1점 고정", "1/2/3 방향 고정으로 강체모드 억제 — 없으면 강성행렬이 특이해진다"],
    ["거시 응력 읽기", "σ = RF(드라이버 반력) / V_box — 메쉬 충전율 100 % 라서 성립"],
  ];
  let iy = 2.42;
  items.forEach((it, i) => {
    chip(s, i + 1, 7.20, iy + 0.04, i < 2 ? EMBER : STEEL, 0.34);
    s.addText(it[0], { x: 7.68, y: iy, w: 5.03, h: 0.30, fontFace: KF, fontSize: 12.5, bold: true, color: INK, margin: 0 });
    s.addText(it[1], { x: 7.68, y: iy + 0.31, w: 5.03, h: 0.62, fontFace: KF, fontSize: 10.5, color: MUTED, margin: 0, lineSpacingMultiple: 1.16 });
    iy += 1.02;
  });

  foot(s, "출처 — verification/PBC_VALIDATION_GUIDE.md · abaqus/meshes/README.md · 논문 §3.2.2 (Xia et al. [31] 인용) · ≈119개는 논문 치수로 계산한 값");
  s.addNotes("논문은 PBC를 '적용했다'고만 쓰고 구속식은 주지 않습니다. 우리는 TexGen이 생성한 Xia 형식을 쓰고, 그 정합성을 직접 검증했습니다(다음 두 장).");
}

// =====================================================================
// 3. Verification (1/2): static audit
// =====================================================================
{
  const s = sl();
  head(s, "PBC — VERIFIED 1/2", "검증 ① 솔버 없이 1초 — 정적 감사 7가지", 25);

  const checks = [
    "격자 — Lx·Ly·Lz 실측, 드라이버가 순수 DOF 운반체인지",
    "세트 페어링 — FaceA[k]·FaceB[k] 가 격자벡터 하나만큼 떨어졌는지",
    "방정식 계수 — 실측 오프셋에서 재유도해 파일 값과 대조",
    "DOF 소거 / 과구속 — 이중 소거, 소거 DOF 의 *Boundary",
    "표면 커버리지 — 모든 표면 절점이 정확히 한 번 구속",
    "강체모드 억제 — 코너 1/2/3 방향 고정 존재",
    "부피분율 — tet 부피 적분, 상 분율이 논문과 일치",
  ];
  let cy = 1.56;
  checks.forEach((c, i) => {
    chip(s, i + 1, M, cy + 0.02, i < 4 ? EMBER : STEEL, 0.32);
    s.addText(c, { x: M + 0.46, y: cy, w: 7.0, h: 0.36, fontFace: KF, fontSize: 11.5, color: INK, valign: "middle", margin: 0 });
    cy += 0.475;
  });

  card(s, 8.40, 1.56, 4.31, 0.92, GREEN);
  s.addText("RESULT: PBC DEFINITION IS CONSISTENT", { x: 8.40, y: 1.64, w: 4.31, h: 0.42, fontFace: MONO, fontSize: 11, bold: true, color: PAPER, align: "center", margin: 0 });
  s.addText("6개 덱 전부 · 경고 0 건", { x: 8.40, y: 2.06, w: 4.31, h: 0.30, fontFace: KF, fontSize: 10.5, color: "C8E0D3", align: "center", margin: 0 });

  card(s, 8.40, 2.62, 4.31, 2.86, TINT);
  const nums = [
    ["V_RVE", "5.390000 mm³ · 충전율 100.0000 %"],
    ["방정식", "57 식 전부 기하학적 정합"],
    ["표면 절점", "9,062 개가 빠짐없이 한 번씩"],
    ["대응 절점", "x 394=394 · y 406=406 · z 3951=3951"],
    ["상 분율", "얀 50.51 % / 기지 49.49 %"],
    ["전체 Vf", "0.5051 × 0.792 = 0.4000"],
  ];
  let ny = 2.80;
  nums.forEach((n) => {
    s.addText(n[0], { x: 8.64, y: ny, w: 1.10, h: 0.40, fontFace: KF, fontSize: 10, bold: true, color: STEEL, valign: "middle", margin: 0 });
    s.addText(n[1], { x: 9.78, y: ny, w: 2.85, h: 0.40, fontFace: KF, fontSize: 9.5, color: INK, valign: "middle", margin: 0 });
    ny += 0.44;
  });

  card(s, M, 5.10, 7.55, 0.86, EMBER_SOFT);
  s.addText("마주보는 면의 절점 수가 정확히 같다 = 메쉬 자체가 주기적. 다르면 TexGen 에서 재생성.", {
    x: M + 0.26, y: 5.10, w: 7.05, h: 0.86, fontFace: KF, fontSize: 11, color: INK, margin: 0, valign: "middle",
  });

  card(s, M, 6.14, CW, 0.72, GRAPHITE);
  s.addText([
    { text: "감사 도구 자체 검증 — ", options: { bold: true, color: EMBER, fontSize: 11.5 } },
    { text: "자주 나는 결함 11종을 일부러 주입 (계수 오류·세트 순서·코너 삭제·비주기 메쉬 등) → ", options: { color: PAPER, fontSize: 11.5 } },
    { text: "ALL 11 FAULTS DETECTED", options: { bold: true, color: "6FBF8F", fontSize: 11.5, fontFace: MONO } },
  ], { x: M + 0.28, y: 6.14, w: CW - 0.56, h: 0.72, fontFace: KF, margin: 0, valign: "middle" });

  foot(s, "출처 — verification/check_pbc.py (실패 시 exit 1, 파이프라인 게이트) · test_check_pbc.py · 174,405 요소 생산 덱 기준");
  s.addNotes("Abaqus 없이 .inp 텍스트만 읽어 1초에 걸러냅니다. '잡지 못하는 검사는 통과와 구별되지 않는다'가 11종 주입의 이유입니다.");
}

// =====================================================================
// 4. Verification (2/2): in-run evidence
// =====================================================================
{
  const s = sl();
  head(s, "PBC — VERIFIED 2/2", "검증 ② 본해석이 준 증거 네 가지", 25);

  const ev = [
    ["드라이버 반력", "6개 전부 0", "구속이 새지 않는다", EMBER],
    ["체적가중 평균응력 잔차", "4.0e−8", "기계정밀도 수준", STEEL],
    ["횡방향 응력", "전 증분 0.000", "단축 인장이 정확히 단축", STEEL],
    ["강성 6×6 대칭성 위반", "0.0000 %", "PBC + 야코비안 동시 검증", GREEN],
  ];
  const ew = 2.94, eg = 0.19;
  ev.forEach((e, i) => {
    const x = M + i * (ew + eg);
    card(s, x, 1.56, ew, 2.55, TINT);
    s.addText(e[0], { x: x + 0.24, y: 1.74, w: ew - 0.48, h: 0.56, fontFace: KF, fontSize: 11, bold: true, color: MUTED, margin: 0, lineSpacingMultiple: 1.1 });
    s.addText(e[1], { x: x + 0.24, y: 2.36, w: ew - 0.48, h: 0.70, fontFace: KF, fontSize: 20, bold: true, color: e[3], margin: 0, valign: "middle" });
    s.addText(e[2], { x: x + 0.24, y: 3.12, w: ew - 0.48, h: 0.80, fontFace: KF, fontSize: 10.5, color: INK, margin: 0, lineSpacingMultiple: 1.18 });
  });

  card(s, M, 4.32, CW, 1.20, GREEN_SOFT);
  s.addText([
    { text: "네 번째가 가장 강하다. ", options: { bold: true, color: GREEN, fontSize: 13 } },
    { text: "손상 후 균질화 강성 6×6 추출에는 대칭을 강제하는 단계가 전혀 없다. 그런데도 C_ij = C_ji (위반 0.0000 %) — 주기경계조건과 UMAT 할선 야코비안이 ", options: { color: INK, fontSize: 13 } },
    { text: "동시에", options: { bold: true, color: INK, fontSize: 13 } },
    { text: " 옳아야만 나오는 값이다.", options: { color: INK, fontSize: 13 } },
  ], { x: M + 0.30, y: 4.32, w: CW - 0.60, h: 1.20, fontFace: KF, margin: 0, valign: "middle", lineSpacingMultiple: 1.22 });

  s.addText("정직하게 남은 것 — 패치 테스트 · 2상 균질화 · EasyPBC 교차검증은 스크립트 준비 완료 · 미실행. RVE 수준 메쉬 수렴성도 미검증.", {
    x: M, y: 5.80, w: CW, h: 0.38, fontFace: KF, fontSize: 11.5, bold: true, color: AMBER, margin: 0, valign: "middle",
  });

  foot(s, "출처 — 랩미팅 브리프 §7 (예상질문) · §4.5 손상 후 균질화 강성 · verification/PBC_VALIDATION_GUIDE.md");
  s.addNotes("'PBC 제대로 걸렸냐'는 질문에는 네 번째 하나만 말해도 충분합니다. 남은 검증(패치 테스트·EasyPBC)은 먼저 밝히고 다음 단계로 두세요.");
}

pres.writeFile({ fileName: require("path").join(__dirname, "CSiC_PBC_RVE_4slides.pptx") }).then((f) => console.log("WROTE", f));
