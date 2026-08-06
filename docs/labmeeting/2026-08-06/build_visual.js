const pptxgen = require("pptxgenjs");
const path = require("path");
const DIR = __dirname;
const F = (p) => path.join(DIR, p);

const INK = "1A1D21", GRAPHITE = "24282E", PAPER = "FFFFFF", TINT = "F1F2F4";
const EMBER = "D9542B", EMBER_SOFT = "FAE7DF", STEEL = "3F6B7D", STEEL_SOFT = "E3ECF0";
const MUTED = "6E7681", ICE = "C6CDD5", GREEN = "2F6B4F", GREEN_SOFT = "E2EEE8";
const GREEN_L = "6FBF8F", AMBER = "9C6B10";
const KF = "맑은 고딕", MONO = "Courier New";
const M = 0.62, CW = 13.333 - 2 * M;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "C/SiC RVE · PBC · UMAT — 시각 자료";

const sl = () => { const s = pres.addSlide(); s.background = { color: PAPER }; return s; };
const sd = () => { const s = pres.addSlide(); s.background = { color: GRAPHITE }; return s; };

function head(s, eyebrow, title, dark, ts) {
  s.addText(eyebrow, { x: M, y: 0.28, w: CW, h: 0.24, fontFace: KF, fontSize: 11,
    bold: true, color: EMBER, charSpacing: 1.4, margin: 0 });
  s.addText(title, { x: M, y: 0.56, w: CW, h: 0.60, fontFace: KF, fontSize: ts || 26,
    bold: true, color: dark ? PAPER : INK, margin: 0, valign: "top" });
}
function foot(s, t, dark) {
  s.addText(t, { x: M, y: 6.98, w: CW, h: 0.28, fontFace: KF, fontSize: 9,
    color: dark ? "8B939C" : MUTED, margin: 0, valign: "middle" });
}
function card(s, x, y, w, h, fill, line) {
  const o = { x, y, w, h, fill: { color: fill }, rectRadius: 0.06 };
  if (line) o.line = { color: line, width: 1 };
  s.addShape(pres.ShapeType.roundRect, o);
}
function chip(s, n, x, y, color, d) {
  d = d || 0.34;
  s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color } });
  s.addText(String(n), { x, y, w: d, h: d, align: "center", valign: "middle", margin: 0,
    fontFace: KF, fontSize: 12, bold: true, color: PAPER });
}

// =====================================================================
// 1. RVE
// =====================================================================
{
  const s = sl();
  head(s, "RVE", "RVE — 논문의 단위셀을 그대로 세운다");

  s.addImage({ path: F("fig_rve.png"), x: M, y: 1.32, w: 8.05, h: 3.60 });

  const stats = [
    ["치수", "3.5 × 3.5 × 0.44 mm", "논문 0.4334 (+1.5 %)"],
    ["얀", "warp 2 ∥ x  ·  weft 2 ∥ y", "타원 단면 1.28 × 0.20 mm"],
    ["섬유체적분율", "Vf = 0.4000", "논문 ≈ 40 % 일치"],
    ["요소", "26,452 C3D4 (경향 확인용)", "생산 덱은 174,405"],
    ["충전율", "100.0000 %", "σ = RF / V_box 가 성립"],
  ];
  card(s, 8.9, 1.32, 3.81, 3.60, TINT);
  let y = 1.46;
  stats.forEach((st) => {
    s.addText(st[0], { x: 9.14, y, w: 3.35, h: 0.22, fontFace: KF, fontSize: 9.5,
      bold: true, color: STEEL, margin: 0 });
    s.addText(st[1], { x: 9.14, y: y + 0.22, w: 3.35, h: 0.26, fontFace: KF, fontSize: 12,
      bold: true, color: INK, margin: 0 });
    s.addText(st[2], { x: 9.14, y: y + 0.46, w: 3.35, h: 0.22, fontFace: KF, fontSize: 9,
      color: MUTED, margin: 0 });
    y += 0.68;
  });

  const bot = [
    ["기지 요소", "15,369", STEEL],
    ["얀 요소", "11,083  (Yarn0–3)", STEEL],
    ["절점", "5,686  ( + 드라이버 6 )", STEEL],
    ["체적", "5.390000 mm³", EMBER],
  ];
  const bw = 2.94, bg = 0.19;
  bot.forEach((b, i) => {
    const x = M + i * (bw + bg);
    card(s, x, 5.14, bw, 1.02, i === 3 ? EMBER_SOFT : STEEL_SOFT);
    s.addText(b[0], { x: x + 0.22, y: 5.24, w: bw - 0.44, h: 0.26, fontFace: KF,
      fontSize: 9.5, color: b[2], margin: 0 });
    s.addText(b[1], { x: x + 0.22, y: 5.50, w: bw - 0.44, h: 0.42, fontFace: KF,
      fontSize: 14, bold: true, color: INK, margin: 0, valign: "middle" });
  });

  s.addText("그림은 실제 TexGen 메쉬(.inp)를 직접 읽어 그린 것 — 얀 표면은 요소 경계면에서 추출", {
    x: M, y: 6.30, w: CW, h: 0.30, fontFace: KF, fontSize: 10, color: MUTED, margin: 0 });
  foot(s, "출처 — abaqus/meshes/CSiC_RVE_0135.inp · abaqus/meshes/README.md · PAPER_DEVIATION_REGISTER §2");
  s.addNotes("TexGen 슬라이드에서 만든 형상이 실제로 이렇게 메쉬가 됩니다. 얀 4개(경사 2, 위사 2)와 기지로 요소가 전부 분류돼 있습니다.");
}

// =====================================================================
// 2. PBC — the actual deck cards
// =====================================================================
{
  const s = sl();
  head(s, "PBC — CODE", "주기경계조건 — 덱에 실제로 들어간 것");

  card(s, M, 1.26, 7.30, 5.10, GRAPHITE);
  s.addText("CSiC_RVE_0135.inp   (발췌, 원문 그대로)", {
    x: M + 0.28, y: 1.40, w: 6.7, h: 0.26, fontFace: KF, fontSize: 10, color: EMBER, margin: 0 });
  s.addText([
    { text: "*NSet, NSet=FaceA, Unsorted\n", options: { color: GREEN_L } },
    { text: "10, 13, 14, 15, 24, 27, 384, 385, ...", options: { color: PAPER } },
    { text: "        ← 58 nodes, x = Lx\n", options: { color: "8B939C" } },
    { text: "*NSet, NSet=FaceB, Unsorted\n", options: { color: GREEN_L } },
    { text: "2, 5, 6, 7, 18, 21, 138, 139, ...", options: { color: PAPER } },
    { text: "     ← 58 nodes, x = 0\n\n", options: { color: "8B939C" } },
    { text: "*Node\n", options: { color: GREEN_L } },
    { text: "5681, 0, 0, 0\n", options: { color: PAPER } },
    { text: "*NSet, NSet=ConstraintsDriver0\n", options: { color: GREEN_L } },
    { text: "5681", options: { color: PAPER } },
    { text: "                        ← e_x 운반 절점\n\n", options: { color: "8B939C" } },
    { text: "*Equation\n3\n", options: { color: GREEN_L } },
    { text: "FaceA, 1, 1.0, FaceB, 1, -1.0,\n     ConstraintsDriver0, 1, -3.5\n", options: { color: "F0B27A" } },
    { text: "*Equation\n2\n", options: { color: GREEN_L } },
    { text: "FaceA, 2, 1.0, FaceB, 2, -1.0\n", options: { color: PAPER } },
    { text: "*Equation\n2\n", options: { color: GREEN_L } },
    { text: "FaceA, 3, 1.0, FaceB, 3, -1.0", options: { color: PAPER } },
  ], { x: M + 0.28, y: 1.74, w: 6.75, h: 4.5, fontFace: MONO, fontSize: 10.5, margin: 0,
       valign: "top", lineSpacingMultiple: 1.06 });

  const notes = [
    ["세트는 순서대로 짝지어진다", "FaceA 의 k번째와 FaceB 의 k번째가 한 쌍. 그래서 Unsorted — 누가 정렬하면 짝이 깨진다."],
    ["−3.5 는 격자길이 Lx", "u_A − u_B = Lx · U(Driver0).  드라이버 변위가 곧 거시 변형률 ε_x."],
    ["y · z 방향은 항이 없다", "x-면 쌍에서 u_y, u_z 의 점프는 0. 즉 ε_yx = ε_zx = 0 — H 가 상삼각인 이유."],
    ["57개 카드 → 3,645개 식", "면 · 모서리 · 꼭짓점까지 표면 절점 전체가 정확히 한 번씩 구속된다."],
  ];
  let ny = 1.26;
  notes.forEach((n, i) => {
    chip(s, i + 1, 8.20, ny + 0.06, i < 2 ? EMBER : STEEL, 0.34);
    s.addText(n[0], { x: 8.68, y: ny, w: 4.03, h: 0.30, fontFace: KF, fontSize: 12.5,
      bold: true, color: INK, margin: 0 });
    s.addText(n[1], { x: 8.68, y: ny + 0.32, w: 4.03, h: 0.86, fontFace: KF, fontSize: 10.5,
      color: MUTED, margin: 0, valign: "top", lineSpacingMultiple: 1.18 });
    ny += 1.30;
  });

  card(s, 8.20, 6.42, 4.51, 0.44, GREEN_SOFT);
  s.addText("코너 1점 고정으로 강체모드 억제", { x: 8.20, y: 6.42, w: 4.51, h: 0.44,
    fontFace: KF, fontSize: 10.5, bold: true, color: GREEN, align: "center",
    valign: "middle", margin: 0 });

  foot(s, "출처 — abaqus/meshes/CSiC_RVE_0135.inp (TexGen 생성, Xia 통일 PBC 형식) · 논문 §3.2.2");
  s.addNotes("이 세 줄이 x방향 주기성 전부입니다. 같은 구조가 y(FaceC/D)와 z(FaceE/F)에도 붙습니다.");
}

// =====================================================================
// 3. UMAT — the actual Fortran
// =====================================================================
{
  const s = sl();
  head(s, "UMAT — CODE", "UMAT — 요소마다 무슨 계산이 도는가");

  const rows = [
    ["상(相) 판별", "IF (INDEX(CMNAME,'YARN').GT.0) THEN\n   CALL KYARN_UPDATE(...)\nELSE IF (INDEX(CMNAME,'MATRIX').GT.0) THEN\n   CALL KMATRIX_UPDATE(...)",
     "재료 이름으로 얀/기지 분기. 같은 UMAT 하나가 두 상을 모두 처리한다.", EMBER],
    ["손상변수", "D = 1.0D0 - EXP(A*(1.0D0-R))/R\nD = MIN(DMAX,MAX(0.0D0,D))",
     "R = 유효응력 / 강도. R ≤ 1 이면 손상 0, 넘으면 지수적으로 진전 · 상한 DMAX.", EMBER],
    ["크랙밴드 정규화", "GLE1   = G01*CELENT\nA1TEFF = 2.0D0*GLE1/(GF1T-GLE1)",
     "요소크기 CELENT 로 연화기울기를 보정 → 메쉬가 바뀌어도 소산에너지가 같다.", STEEL],
    ["비가역 + 점성", "GAM = DTIME/(ETA+DTIME)\nD1T = MAX(D1T0, D1T0+GAM*(TAR-D1T0))",
     "MAX 가 비가역성을 보장 — 한 번 생긴 손상은 안 풀린다. GAM 은 수치 안정화.", STEEL],
    ["강성 저하 · 야코비안", "RSC(1)=SQRT(1.0D0-D1)\n...\nCD = R*C0*R      →   CTAN(I,J)=CD(I,J)",
     "Cd = R·C0·R 형태라 대칭 양정치가 보장된다. 이 대칭성이 균질화 강성 검증으로 되돌아온다.", GREEN],
  ];
  let y = 1.20;
  rows.forEach((r, i) => {
    chip(s, i + 1, M, y + 0.30, r[3], 0.34);
    s.addText(r[0], { x: M + 0.46, y: y + 0.02, w: 1.85, h: 0.9, fontFace: KF, fontSize: 11.5,
      bold: true, color: INK, margin: 0, valign: "middle", lineSpacingMultiple: 1.1 });
    card(s, 2.98, y, 5.62, 1.00, GRAPHITE);
    s.addText(r[1], { x: 3.14, y, w: 5.36, h: 1.00, fontFace: MONO, fontSize: 9,
      color: PAPER, margin: 0, valign: "middle", lineSpacingMultiple: 1.06 });
    s.addText(r[2], { x: 8.78, y, w: 3.93, h: 1.00, fontFace: KF, fontSize: 10.5,
      color: MUTED, margin: 0, valign: "middle", lineSpacingMultiple: 1.18 });
    y += 1.02;
  });

  card(s, M, 6.34, CW, 0.52, EMBER_SOFT);
  s.addText([
    { text: "미구현 (먼저 밝힐 것) — ", options: { bold: true, color: EMBER } },
    { text: "기지 소성 (논문 Eq.6–10) · 얀 종방향 Eq.17/18 혼합 선형-지수형. 현재는 탄성-손상만.",
      options: { color: INK } },
  ], { x: M + 0.28, y: 6.34, w: CW - 0.56, h: 0.52, fontFace: KF, fontSize: 10.5,
       margin: 0, valign: "middle" });

  foot(s, "출처 — src/UMAT_CSIC_RVE_DAMAGE_V2_7.for (코드 원문 발췌, 865줄)");
  s.addNotes("코드를 다 읽을 필요는 없고, 다섯 덩어리로 나뉜다는 것만 보여주면 됩니다. 5번의 대칭성이 다음 장 검증으로 이어집니다.");
}

// =====================================================================
// 4. It works — visual proof
// =====================================================================
{
  const s = sl();
  head(s, "DOES IT WORK", "돌려보면 — 변형된 셀이 빈틈없이 이어 붙는다", false, 25);

  s.addImage({ path: F("fig_tile.png"), x: M, y: 1.16, w: 9.10, h: 4.55 });

  card(s, 9.90, 1.16, 2.81, 4.55, TINT);
  s.addText("검증 수치", { x: 10.12, y: 1.34, w: 2.4, h: 0.28, fontFace: KF,
    fontSize: 12, bold: true, color: STEEL, margin: 0 });
  const ev = [
    ["타일 이음매 어긋남", "4.4e−16 mm"],
    ["마주보는 면\n절점 패턴 차이", "0.0 mm"],
    ["58쌍 변위 점프\n최대 편차", "0.0 mm"],
    ["응력장 균일도", "2.1e−12"],
    ["균질화 강성 오차", "5.4e−15"],
    ["충전율", "100.0000 %"],
  ];
  let y = 1.60;
  ev.forEach((e) => {
    s.addText(e[0], { x: 10.12, y, w: 2.4, h: 0.34, fontFace: KF, fontSize: 9,
      color: MUTED, margin: 0, valign: "top", lineSpacingMultiple: 1.05 });
    s.addText(e[1], { x: 10.12, y: y + 0.30, w: 2.4, h: 0.32, fontFace: KF, fontSize: 13,
      bold: true, color: GREEN, margin: 0, valign: "middle" });
    y += 0.66;
  });

  card(s, M, 5.86, CW, 1.00, GREEN_SOFT);
  s.addText([
    { text: "무엇을 본 것인가.  ", options: { bold: true, color: GREEN, fontSize: 12.5 } },
    { text: "등방 재료 하나만 채우고 거시 변형률을 걸면 정답이 닫힌 형태로 알려져 있다(패치 테스트). 26,452개 요소의 응력이 전부 같고, 변형된 셀을 3×3 으로 깔면 이음매가 ", options: { color: INK, fontSize: 12.5 } },
    { text: "기계정밀도", options: { bold: true, color: INK, fontSize: 12.5 } },
    { text: "로 맞는다 — 구속이 새면 절대 나올 수 없는 결과다.", options: { color: INK, fontSize: 12.5 } },
  ], { x: M + 0.30, y: 5.86, w: CW - 0.60, h: 1.00, fontFace: KF, margin: 0,
       valign: "middle", lineSpacingMultiple: 1.2 });

  foot(s, "실제 덱(.inp)의 절점·요소·*Equation 을 그대로 읽어 Python(numpy/scipy)으로 독립 재현한 결과 — Abaqus 패치 테스트는 아직 별도로 돌려야 함");
  s.addNotes("이 장이 '노드·요소가 PBC로 잘 맞춰져 움직인다'의 답입니다. 주의: Abaqus가 아니라 Python 독립 재현이라고 반드시 밝히세요. 구속식 자체가 옳다는 증명이지, Abaqus 실행 검증을 대체하지는 않습니다.");
}

// =====================================================================
// 5-6. Appendix
// =====================================================================
{
  const s = sl();
  head(s, "부록 A", "마주보는 면이 정말로 한 몸인가", false, 25);
  s.addImage({ path: F("fig_pair.png"), x: M, y: 1.40, w: 12.09, h: 4.66 });
  s.addText("왼쪽 — z 방향 두 면(각 925 절점)의 절점 배치가 완전히 겹친다. 메쉬 자체가 주기적이라는 뜻.        오른쪽 — 인장 시 x 면 58쌍의 변위 점프가 전부 ε·Lx 위에 정확히 놓인다.", {
    x: M, y: 6.20, w: CW, h: 0.56, fontFace: KF, fontSize: 10.5, color: INK,
    margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });
  foot(s, "abaqus/meshes/CSiC_RVE_0135.inp + Python 독립 재현");
  s.addNotes("질문이 나오면 쓰는 장입니다.");
}
{
  const s = sl();
  head(s, "부록 B", "패치 테스트 — 26,452개 요소가 전부 같은 응력", false, 25);
  s.addImage({ path: F("fig_patch.png"), x: M, y: 1.60, w: 12.09, h: 3.96 });
  card(s, M, 5.80, CW, 0.96, TINT);
  s.addText("가로축 단위가 10⁻¹⁰ MPa 다. 인장 388.888889 MPa · 전단 145.833333 MPa 로 이론값과 소수점 6자리까지 일치하고, 요소 간 퍼짐은 10⁻¹⁰ MPa 수준이다.", {
    x: M + 0.30, y: 5.80, w: CW - 0.60, h: 0.96, fontFace: KF, fontSize: 12,
    color: INK, margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });
  foot(s, "등방 재료 E = 350 GPa, ν = 0.2 (논문 Table 2 의 SiC 기지) · ε = 10⁻³");
  s.addNotes("판정 기준이 '그럴듯한가'가 아니라 '1e-12인가'라는 점이 핵심입니다.");
}

pres.writeFile({ fileName: F("CSiC_RVE_PBC_UMAT_visual.pptx") })
    .then((f) => console.log("WROTE", f));
