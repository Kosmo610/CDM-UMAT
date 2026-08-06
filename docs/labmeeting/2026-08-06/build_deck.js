const pptxgen = require("pptxgenjs");
const path = require("path");

const DIR = __dirname;   // figs/ and the output .pptx live next to this script
const F = (p) => path.join(DIR, p);

// ---------- palette : graphite (carbon) / ceramic / ember (1050 C) ----------
const INK        = "1A1D21";
const GRAPHITE   = "24282E";
const GCARD      = "333941";
const PAPER      = "FFFFFF";
const TINT       = "F1F2F4";
const TINT2      = "E6E9ED";
const EMBER      = "D9542B";
const EMBER_SOFT = "FAE7DF";
const STEEL      = "3F6B7D";
const STEEL_SOFT = "E3ECF0";
const MUTED      = "6E7681";
const ICE        = "C6CDD5";
const GREEN      = "2F6B4F";
const GREEN_SOFT = "E2EEE8";
const AMBER      = "9C6B10";
const AMBER_SOFT = "F6EDD9";
const STEEL_L    = "7FB0C4";
const GREEN_L    = "6FBF8F";

const KF = "맑은 고딕";
const MONO = "Courier New";

const M = 0.62;                 // page margin
const CW = 13.333 - 2 * M;      // content width

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";     // 13.333 x 7.5
pres.author = "CSIC RVE study";
pres.title = "C/SiC 평직 복합재 RVE 구축과 주기경계조건 검증";

// ---------- helpers ----------
function sd() { const s = pres.addSlide(); s.background = { color: GRAPHITE }; return s; }
function sl() { const s = pres.addSlide(); s.background = { color: PAPER }; return s; }

function head(s, eyebrow, title, dark, opts) {
  opts = opts || {};
  s.addText(eyebrow, {
    x: M, y: 0.30, w: CW, h: 0.24, fontFace: KF, fontSize: 11, bold: true,
    color: dark ? EMBER : EMBER, charSpacing: 1.4, margin: 0,
  });
  s.addText(title, {
    x: M, y: 0.58, w: opts.tw || CW, h: opts.th || 0.72, fontFace: KF,
    fontSize: opts.ts || 29, bold: true, color: dark ? PAPER : INK, margin: 0, valign: "top",
  });
}

function foot(s, text, dark) {
  s.addText(text, {
    x: M, y: 6.92, w: CW, h: 0.30, fontFace: KF, fontSize: 9,
    color: dark ? "8B939C" : MUTED, margin: 0, valign: "middle",
  });
}

function chip(s, n, x, y, color, d) {
  d = d || 0.40;
  s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color } });
  s.addText(String(n), {
    x, y, w: d, h: d, align: "center", valign: "middle", margin: 0,
    fontFace: KF, fontSize: d > 0.42 ? 15 : 13, bold: true, color: PAPER,
  });
}

function card(s, x, y, w, h, fill, line) {
  const o = { x, y, w, h, fill: { color: fill } };
  if (line) o.line = { color: line, width: 1 };
  s.addShape(pres.ShapeType.roundRect, Object.assign(o, { rectRadius: 0.06 }));
}

function tbl(s, rows, x, y, w, colW, opts) {
  opts = opts || {};
  s.addTable(rows, {
    x, y, w, colW,
    rowH: opts.rowH || 0.34,
    fontFace: KF, fontSize: opts.fs || 11.5, color: INK,
    border: { type: "solid", color: "DCE0E5", pt: 1 },
    align: "left", valign: "middle",
    margin: opts.margin === undefined ? 0.07 : opts.margin,
  });
}

function hdrRow(cells, fill) {
  return cells.map((t) => ({
    text: t,
    options: { bold: true, color: PAPER, fill: { color: fill || STEEL }, fontSize: 11 },
  }));
}

// =====================================================================
// 1. TITLE
// =====================================================================
{
  const s = sd();
  s.addImage({ path: F("figs/fig2c.png"), x: 7.35, y: 2.28, w: 5.35, h: 3.28 });
  s.addText("랩미팅 · 2026-08-06", {
    x: M, y: 1.16, w: 6.4, h: 0.3, fontFace: KF, fontSize: 12, bold: true,
    color: EMBER, charSpacing: 1.6, margin: 0,
  });
  s.addText("C/SiC 평직 복합재\nRVE 구축과 주기경계조건 검증", {
    x: M, y: 1.62, w: 6.6, h: 1.75, fontFace: KF, fontSize: 34, bold: true,
    color: PAPER, margin: 0, lineSpacingMultiple: 1.12,
  });
  s.addText("TexGen 형상 모델링 · PBC 적용 · RVE 검증 · 해석 조립", {
    x: M, y: 3.52, w: 6.6, h: 0.42, fontFace: KF, fontSize: 15, color: ICE, margin: 0,
  });
  s.addShape(pres.ShapeType.line, { x: M, y: 4.16, w: 2.2, h: 0, line: { color: EMBER, width: 2.5 } });
  s.addText([
    { text: "재현 대상\n", options: { fontSize: 10, color: "8B939C", bold: true } },
    { text: "Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang,\n", options: { fontSize: 11.5, color: ICE } },
    { text: "“Effect of thermal residual stress on the tensile properties and damage\nprocess of C/SiC composites at high temperatures”\n", options: { fontSize: 11.5, color: PAPER, italic: true } },
    { text: "Ceramics International 48 (2022) 3109–3124", options: { fontSize: 11.5, color: ICE } },
  ], { x: M, y: 4.42, w: 6.6, h: 1.6, fontFace: KF, margin: 0, lineSpacingMultiple: 1.22 });
  s.addText("논문 Fig. 2(c) — TexGen으로 생성한 평직 RVC", {
    x: 7.35, y: 5.66, w: 5.35, h: 0.3, fontFace: KF, fontSize: 9.5, color: "8B939C",
    align: "center", margin: 0,
  });
  s.addNotes("오늘은 손상 결과가 아니라 '모델을 어떻게 만들었는가'를 다룹니다. 논문 재현의 앞 절반, 즉 형상·경계조건·검증까지입니다.");
}

// =====================================================================
// 2. 오늘의 범위
// =====================================================================
{
  const s = sl();
  head(s, "SCOPE", "오늘 다룰 것 — 모델이 만들어지기까지", false);

  const steps = [
    ["논문 시편\n→ RVE 정의", "185 mm 시편에서\n단위셀 하나를 잘라낸다", EMBER],
    ["TexGen\n형상 · 메쉬", "CT → 타원 특성화\n→ 평직 RVC 생성", EMBER],
    ["주기경계조건\n적용", "*Equation 57식\n+ 드라이버 절점 6개", STEEL],
    ["RVE · PBC\n검증", "솔버 없는 감사\n+ 본해석 증거", STEEL],
    ["재료카드 조립\n→ 해석", "UMAT 물성 + 3스텝\n(냉각·승온·인장)", GREEN],
  ];
  const w = 2.26, gap = 0.2;
  steps.forEach((st, i) => {
    const x = M + i * (w + gap);
    card(s, x, 1.62, w, 3.00, TINT);
    chip(s, i + 1, x + 0.24, 1.86, st[2], 0.44);
    s.addText(st[0], {
      x: x + 0.24, y: 2.56, w: w - 0.48, h: 0.9, fontFace: KF, fontSize: 14.5,
      bold: true, color: INK, margin: 0, lineSpacingMultiple: 1.1,
    });
    s.addText(st[1], {
      x: x + 0.24, y: 3.52, w: w - 0.48, h: 0.9, fontFace: KF, fontSize: 10.5,
      color: MUTED, margin: 0, lineSpacingMultiple: 1.16,
    });
  });

  card(s, M, 5.06, CW, 1.30, EMBER_SOFT);
  s.addText([
    { text: "오늘의 결론  ", options: { bold: true, color: EMBER, fontSize: 13 } },
    { text: "형상은 논문과 같게 맞췄고, 경계조건은 솔버 없이도 · 본해석에서도 옳다는 것이 확인됐다.\n" , options: { fontSize: 13, color: INK } },
    { text: "손상 결과와 논문 불일치 분석은 다음 회차에서 다룹니다.", options: { fontSize: 11.5, color: MUTED } },
  ], { x: M + 0.3, y: 5.06, w: CW - 0.6, h: 1.30, fontFace: KF, margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });

  foot(s, "CDM-UMAT · C/SiC 평직 RVE 손상해석", false);
  s.addNotes("다섯 단계 중 오늘은 1~5 전부를 훑되, 무게중심은 3(PBC)과 4(검증)에 둡니다.");
}

// =====================================================================
// 3. 진행 상황
// =====================================================================
{
  const s = sl();
  head(s, "STATUS", "지금 어디까지 왔나", false);

  const done = [
    ["완료", "RVE 형상 · 메쉬 (TexGen)", "174,405 C3D4 · 3.5 × 3.5 × 0.44 mm", GREEN],
    ["완료", "주기경계조건 + 정적 감사", "6개 덱 전부 통과 · 경고 0건", GREEN],
    ["완료", "얀 미시역학 균질화", "Chamis / Schapery · 오차 0.005 % 이내", GREEN],
    ["완료", "UMAT 연속체손상역학 구현", "V1_0 → V2_7", GREEN],
    ["완료", "냉각 · 승온 · 인장 3스텝 해석", "23 / 500 / 1000 °C", GREEN],
    ["완료", "손상 후 균질화 강성 6×6 추출", "새 해석 없이 기존 odb 에서", GREEN],
    ["진행", "PAPERFAITH 체인 P0 / P1 / P2", "3개 동시 실행 중", AMBER],
    ["예정", "기지 소성 · 얀 Eq.17/18 · 메쉬 수렴성", "미구현 / 미검증", MUTED],
  ];
  let y = 1.58;
  done.forEach((d) => {
    const soft = d[3] === GREEN ? GREEN_SOFT : d[3] === AMBER ? AMBER_SOFT : TINT2;
    card(s, M, y, 8.05, 0.58, TINT);
    s.addShape(pres.ShapeType.roundRect, { x: M + 0.14, y: y + 0.13, w: 0.62, h: 0.32, fill: { color: soft }, rectRadius: 0.05 });
    s.addText(d[0], { x: M + 0.14, y: y + 0.13, w: 0.62, h: 0.32, fontFace: KF, fontSize: 9.5, bold: true, color: d[3], align: "center", valign: "middle", margin: 0 });
    s.addText(d[1], { x: M + 0.92, y: y + 0.05, w: 3.95, h: 0.48, fontFace: KF, fontSize: 12, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(d[2], { x: M + 4.92, y: y + 0.05, w: 3.0, h: 0.48, fontFace: KF, fontSize: 10, color: MUTED, valign: "middle", margin: 0 });
    y += 0.66;
  });

  // right column
  card(s, 9.0, 1.58, 3.71, 2.62, GRAPHITE);
  s.addText("논문 대비 편차 등록부", { x: 9.24, y: 1.76, w: 3.25, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: PAPER, margin: 0 });
  const reg = [["51", "논문과 동일함이 검증됨", ICE], ["19", "논문에 없어 임의로 정함", "F0B27A"], ["1", "논문에 없어 역보정함", EMBER], ["6", "논문과 명시적으로 다름", "F0B27A"]];
  let ry = 2.18;
  reg.forEach((r) => {
    s.addText(r[0], { x: 9.24, y: ry, w: 0.78, h: 0.44, fontFace: KF, fontSize: 20, bold: true, color: r[2], align: "right", valign: "middle", margin: 0 });
    s.addText(r[1], { x: 10.12, y: ry, w: 2.4, h: 0.44, fontFace: KF, fontSize: 10.5, color: ICE, valign: "middle", margin: 0 });
    ry += 0.5;
  });

  card(s, 9.0, 4.32, 1.78, 1.28, STEEL_SOFT);
  s.addText("UMAT", { x: 9.0, y: 4.44, w: 1.78, h: 0.26, fontFace: KF, fontSize: 10, color: STEEL, align: "center", margin: 0 });
  s.addText("V2_7", { x: 9.0, y: 4.70, w: 1.78, h: 0.6, fontFace: KF, fontSize: 26, bold: true, color: STEEL, align: "center", valign: "middle", margin: 0 });

  card(s, 10.93, 4.32, 1.78, 1.28, EMBER_SOFT);
  s.addText("해석 트랙", { x: 10.93, y: 4.44, w: 1.78, h: 0.26, fontFace: KF, fontSize: 10, color: EMBER, align: "center", margin: 0 });
  s.addText("Lv 8/10", { x: 10.93, y: 4.70, w: 1.78, h: 0.6, fontFace: KF, fontSize: 23, bold: true, color: EMBER, align: "center", valign: "middle", margin: 0 });

  s.addText("형상 · 경계조건 · 물성 · 구성모델은 서 있다.\n남은 것은 손상 물리를 논문 수준으로 끌어올리는 일.", {
    x: 9.0, y: 5.72, w: 3.71, h: 0.8, fontFace: KF, fontSize: 10.5, color: MUTED, margin: 0, lineSpacingMultiple: 1.2,
  });

  foot(s, "출처 — verification/PAPER_DEVIATION_REGISTER.md §0, 랩미팅 브리프 §3·§8", false);
  s.addNotes("등록부 숫자가 이 발표의 정직성 장치입니다. 맞은 것뿐 아니라 임의로 정한 19건, 역보정 1건을 먼저 밝힙니다.");
}

// =====================================================================
// 4. 대상 논문
// =====================================================================
{
  const s = sl();
  head(s, "TARGET PAPER", "재현 대상 — Zhang et al. (2022)", false);

  card(s, M, 1.58, 5.65, 4.5, TINT);
  const meta = [
    ["출처", "Ceramics International 48 (2022) 3109–3124"],
    ["재료", "2D 평직(plain-weave) C/SiC"],
    ["공정", "PIP · 제조온도 1050 °C · Vf ≈ 40 %"],
    ["실험", "진공 · ASTM C1359-13 · 0.5 mm/min"],
    ["시편 수", "온도당 5개 · 23 / 500 / 1000 °C"],
    ["해석", "Abaqus UMAT · 점진적 손상 (CDM)"],
  ];
  let my = 1.86;
  meta.forEach((m) => {
    s.addText(m[0], { x: M + 0.28, y: my, w: 1.05, h: 0.38, fontFace: KF, fontSize: 10.5, bold: true, color: EMBER, valign: "middle", margin: 0 });
    s.addText(m[1], { x: M + 1.38, y: my, w: 4.0, h: 0.38, fontFace: KF, fontSize: 11.5, color: INK, valign: "middle", margin: 0 });
    my += 0.62;
  });

  s.addText("재현 목표 — 논문 Table 3", { x: 6.72, y: 1.58, w: 6.0, h: 0.3, fontFace: KF, fontSize: 13, bold: true, color: INK, margin: 0 });
  tbl(s, [
    hdrRow(["온도", "실험 평균 [MPa]", "논문 해석 [MPa]", "논문 오차"]),
    ["23 °C", "116.17 ± 8.78", "128.45", "10.31 %"],
    ["500 °C", "160.19 ± 14.83", "179.42", "12.00 %"],
    ["1000 °C", "173.28 ± 12.94", "199.15", "14.93 %"],
  ], 6.72, 1.96, 6.0, [1.2, 1.85, 1.65, 1.3], { rowH: 0.42 });

  card(s, 6.72, 3.72, 6.0, 2.36, GRAPHITE);
  s.addText("논문의 주장", { x: 6.96, y: 3.9, w: 5.5, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: EMBER, margin: 0 });
  s.addText([
    { text: "냉각(1050 → 23 °C) 시 CTE 불일치로 기지에 인장 · 얀에 압축 잔류응력", options: { bullet: true, breakLine: true } },
    { text: "그 인장 잔류응력이 상온에서 기지를 미리 손상시켜 강도를 깎는다", options: { bullet: true, breakLine: true } },
    { text: "시험온도를 올리면 잔류응력이 완화 · 반전되어 강도가 오른다", options: { bullet: true, breakLine: true } },
    { text: "23 °C 대비 +39.7 % (500 °C) · +55.0 % (1000 °C)", options: { bullet: true, bold: true, color: PAPER } },
  ], { x: 6.96, y: 4.24, w: 5.5, h: 1.7, fontFace: KF, fontSize: 11.5, color: ICE, margin: 0, paraSpaceAfter: 6 });

  foot(s, "출처 — 논문 Table 3, §2 Experimental procedure · §3.2.4 Analysis procedure", false);
  s.addNotes("논문 해석값은 실험 평균보다 10~15% 높습니다. 우리가 맞춰야 하는 대상은 '논문 해석값'입니다.");
}

// =====================================================================
// 5. 논문의 시편
// =====================================================================
{
  const s = sl();
  head(s, "SPECIMEN", "논문의 시편 — 여기서 출발한다", false);

  card(s, M, 1.6, 7.55, 3.05, TINT);
  s.addImage({ path: F("figs/fig1_spec.png"), x: M + 0.22, y: 1.78, w: 7.11, h: 2.7 });
  s.addText("논문 Fig. 1 — 인장 시편 형상 (단위: mm)", { x: M, y: 4.7, w: 7.55, h: 0.28, fontFace: KF, fontSize: 9.5, color: MUTED, align: "center", margin: 0 });

  const dims = [
    ["전장", "185 mm"],
    ["게이지 길이", "30 mm"],
    ["게이지 폭", "6 mm"],
    ["파지부 폭", "10 mm"],
    ["두께", "3.5 mm"],
    ["필렛", "R15 / R10 · 17°"],
  ];
  card(s, 8.42, 1.6, 4.29, 3.05, STEEL_SOFT);
  s.addText("시편 제원", { x: 8.66, y: 1.76, w: 3.8, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: STEEL, margin: 0 });
  let dy = 2.14;
  dims.forEach((d) => {
    s.addText(d[0], { x: 8.66, y: dy, w: 1.85, h: 0.36, fontFace: KF, fontSize: 11, color: INK, valign: "middle", margin: 0 });
    s.addText(d[1], { x: 10.55, y: dy, w: 1.9, h: 0.36, fontFace: KF, fontSize: 11.5, bold: true, color: STEEL, align: "right", valign: "middle", margin: 0 });
    dy += 0.4;
  });

  card(s, M, 4.98, CW, 1.44, EMBER_SOFT);
  s.addText("문제", { x: M + 0.3, y: 5.14, w: 0.8, h: 0.32, fontFace: KF, fontSize: 12, bold: true, color: EMBER, margin: 0 });
  s.addText("이 시편의 게이지부 안에는 평직 단위셀이 100개 넘게 반복되어 있다. 전부 모델링할 수 없다.\n대신 단위셀 하나만 그리고, 주기경계조건으로 “무한히 반복된 것처럼” 만든다.", {
    x: M + 1.16, y: 5.1, w: CW - 1.5, h: 1.0, fontFace: KF, fontSize: 13.5, color: INK, margin: 0, valign: "middle", lineSpacingMultiple: 1.25,
  });

  foot(s, "출처 — 논문 Fig. 1 (치수 직접 판독)", false);
  s.addNotes("게이지부는 30 × 6 × 3.5 mm 입니다. 다음 장에서 이 안에 단위셀이 몇 개 들어가는지 계산합니다.");
}

// =====================================================================
// 6. 시편 -> RVE  (HERO, dark)
// =====================================================================
{
  const s = sd();
  head(s, "SPECIMEN → RVE", "시편을 다 못 그린다 — 그래서 단위셀 하나", true);

  const boxes = [
    ["시편 게이지부", "30 × 6 × 3.5 mm", "630 mm³", EMBER],
    ["평직 단위셀 = RVE", "3.5 × 3.5 × 0.4334 mm", "5.31 mm³", STEEL_L],
    ["둘의 비", "게이지부 ÷ RVE", "≈ 119 개", GREEN_L],
  ];
  const bw = 3.66, bgap = 0.55;
  boxes.forEach((b, i) => {
    const x = M + i * (bw + bgap);
    card(s, x, 1.62, bw, 2.16, GCARD);
    s.addText(b[0], { x: x + 0.26, y: 1.8, w: bw - 0.52, h: 0.3, fontFace: KF, fontSize: 11.5, bold: true, color: b[3], margin: 0 });
    s.addText(b[1], { x: x + 0.26, y: 2.12, w: bw - 0.52, h: 0.32, fontFace: KF, fontSize: 11, color: ICE, margin: 0 });
    s.addText(b[2], { x: x + 0.26, y: 2.56, w: bw - 0.52, h: 0.9, fontFace: KF, fontSize: 32, bold: true, color: PAPER, margin: 0, valign: "middle" });
    if (i < 2) {
      s.addText("▶", { x: x + bw + 0.06, y: 2.4, w: 0.44, h: 0.5, fontFace: KF, fontSize: 17, color: "6E7681", align: "center", valign: "middle", margin: 0 });
    }
  });

  const facts = [
    ["3.5 mm", "평직 1주기 — 타원 폭 1.28 mm 얀이 warp 2 · weft 2 로 교차"],
    ["0.4334 mm", "1 ply 두께 — 시편 3.5 mm ÷ 0.4334 ≈ 8 층에 해당"],
    ["Vf 40 %", "얀 체적분율 × 얀 내부 섬유분율 → 시편과 동일한 섬유량"],
  ];
  let fy = 4.06;
  facts.forEach((f) => {
    s.addText(f[0], { x: M, y: fy, w: 1.55, h: 0.42, fontFace: KF, fontSize: 14, bold: true, color: EMBER, valign: "middle", margin: 0 });
    s.addText(f[1], { x: M + 1.65, y: fy, w: CW - 1.65, h: 0.42, fontFace: KF, fontSize: 12.5, color: ICE, valign: "middle", margin: 0 });
    fy += 0.5;
  });

  card(s, M, 5.66, CW, 1.02, "3A2C25");
  s.addText([
    { text: "PBC 가 이 축소를 정당화한다. ", options: { bold: true, color: EMBER, fontSize: 14 } },
    { text: "RVE 하나에 주기경계조건을 걸면, 그 셀은 무한히 반복된 매질의 한 조각으로 거동한다.", options: { color: PAPER, fontSize: 14 } },
  ], { x: M + 0.32, y: 5.66, w: CW - 0.64, h: 1.02, fontFace: KF, margin: 0, valign: "middle" });

  foot(s, "체적 630 / 5.31 mm³ 와 8층은 논문 치수로부터 계산한 값 — 논문에 명시된 수치가 아님", true);
  s.addNotes("여기가 '논문과 같은 시편에 RVE를 어떻게 넣었나'에 대한 답입니다. 시편을 축소한 것이 아니라, 시편을 이루는 반복 단위를 뽑아낸 것입니다. 119개, 8층은 제가 논문 치수로 계산한 값이라고 반드시 밝히세요.");
}

// =====================================================================
// 7. 논문의 모델링 절차 (Fig.2)
// =====================================================================
{
  const s = sl();
  head(s, "TEXGEN", "논문의 형상 모델링 — CT → 타원 → TexGen", false);

  card(s, M, 1.56, CW, 2.72, TINT);
  s.addImage({ path: F("figs/p5-000.png"), x: M + 0.26, y: 1.78, w: 11.57, h: 2.31 });
  s.addText("논문 Fig. 2 — Modeling process", { x: M, y: 4.06, w: CW, h: 0.26, fontFace: KF, fontSize: 9.5, color: MUTED, align: "center", margin: 0 });

  const panes = [
    ["(a) CT 스캔", "X-ray CT · 120 kV / 300 μA\nvoxel 0.2 mm — 실제 내부 구조 획득", EMBER],
    ["(b) 타원 특성화", "얀 단면을 타원으로 근사\n장축 1.28 mm · 단축 0.20 mm", EMBER],
    ["(c) TexGen 생성", "평직 RVC 생성\n3.5 × 3.5 × 0.4334 mm · Vf 40 %", STEEL],
  ];
  const pw = 3.9, pg = 0.24;
  panes.forEach((p, i) => {
    const x = M + i * (pw + pg);
    card(s, x, 4.42, pw, 1.5, i === 2 ? STEEL_SOFT : PAPER, "DCE0E5");
    s.addText(p[0], { x: x + 0.24, y: 4.58, w: pw - 0.48, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: p[2], margin: 0 });
    s.addText(p[1], { x: x + 0.24, y: 4.92, w: pw - 0.48, h: 0.86, fontFace: KF, fontSize: 11, color: INK, margin: 0, lineSpacingMultiple: 1.2 });
  });

  s.addText("Fig. 2(c) 의 좌표축이 그대로 증거다 — X · Y : −0.875 ~ 2.625 (= 3.5 mm),  Z : −0.0197 ~ 0.4137 (= 0.4334 mm)", {
    x: M, y: 6.08, w: CW, h: 0.36, fontFace: KF, fontSize: 11.5, color: STEEL, bold: true, margin: 0, valign: "middle",
  });

  foot(s, "출처 — 논문 §3.2.1 RVC model, Fig. 2", false);
  s.addNotes("논문도 TexGen을 씁니다. 우리가 다른 도구를 쓴 게 아니라 같은 도구로 같은 형상을 만든 것입니다.");
}

// =====================================================================
// 8. 우리 RVE 대조표
// =====================================================================
{
  const s = sl();
  head(s, "OUR RVE", "우리 RVE — 무엇이 같고 무엇이 다른가", false);

  const rows = [
    hdrRow(["항목", "논문", "우리 모델", "판정"]),
    ["RVE 평면 치수", "3.5 × 3.5 mm", "3.5 × 3.5 mm", "일치"],
    ["RVE 두께", "0.4334 mm", "0.44 mm", "+1.5 %"],
    ["얀 단면 타원", "1.28 × 0.20 mm", "1.28 × 0.20 mm", "일치"],
    ["섬유체적분율 Vf", "40 %", "0.400", "일치"],
    ["요소", "116,724 C3D4", "174,405 C3D4", "1.49 배"],
    ["특성 요소크기", "명시 없음", "0.0314 mm (체적가중)", "—"],
    ["형상 생성 도구", "TexGen", "TexGen", "일치"],
  ];
  const r = rows.map((row, i) => {
    if (i === 0) return row;
    const v = row[3];
    const col = v === "일치" ? GREEN : v === "—" ? MUTED : AMBER;
    return [row[0], row[1], { text: row[2], options: { bold: true } }, { text: v, options: { bold: true, color: col } }];
  });
  tbl(s, r, M, 1.58, 8.05, [2.35, 2.1, 2.35, 1.25], { rowH: 0.44, fs: 11.5 });

  card(s, 9.0, 1.58, 3.71, 1.98, EMBER_SOFT);
  s.addText("요소 수가 1.49 배", { x: 9.24, y: 1.76, w: 3.25, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: EMBER, margin: 0 });
  s.addText("논문보다 촘촘하다. 재료점 수준에서는 요소크기 0.0285–0.2000 mm 에 대해 소산에너지 편차 1.00000 배로 검증했으나, RVE 수준 메쉬 수렴은 아직 미검증이다.", {
    x: 9.24, y: 2.12, w: 3.25, h: 1.32, fontFace: KF, fontSize: 10.5, color: INK, margin: 0, lineSpacingMultiple: 1.2,
  });

  card(s, 9.0, 3.7, 3.71, 1.93, TINT);
  s.addText("경향 확인용 coarse 메쉬", { x: 9.24, y: 3.86, w: 3.25, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: STEEL, margin: 0 });
  s.addText("26,452 C3D4 · 5,686 절점\nVf 39.46 % · le ≈ 0.102 mm\n같은 재료카드 · 같은 스텝 재사용", {
    x: 9.24, y: 4.22, w: 3.25, h: 1.24, fontFace: KF, fontSize: 10.5, color: INK, margin: 0, lineSpacingMultiple: 1.3,
  });

  card(s, M, 5.14, 8.05, 1.42, GREEN_SOFT);
  s.addText("두께 +1.5 % 를 뺀 나머지 형상 파라미터는 논문과 정확히 같다. 형상은 재현 논쟁의 대상이 아니다.", {
    x: M + 0.3, y: 5.14, w: 7.45, h: 1.42, fontFace: KF, fontSize: 12.5, color: INK, margin: 0, valign: "middle", lineSpacingMultiple: 1.2,
  });

  foot(s, "출처 — PAPER_DEVIATION_REGISTER §2, 랩미팅 브리프 §3.1, abaqus/meshes/README.md", false);
  s.addNotes("두께 0.44는 메쉬 생성 편의상 반올림한 값입니다. +1.5%가 결과에 미치는 영향은 아직 별도로 분리해 보지 않았습니다.");
}

// =====================================================================
// 9. TexGen 출력 3종
// =====================================================================
{
  const s = sl();
  head(s, "TEXGEN OUTPUT", "TexGen이 내놓는 것 — 세 파일은 한 세트", false);

  const files = [
    [".inp", "메쉬 · 요소집합", "절점 / C3D4 요소\nElSet: Matrix, Yarn0–Yarn3\n주기경계 *Equation 57식\n드라이버 절점 6개", EMBER],
    [".ori", "요소별 섬유 방향", "요소마다 방향 2벡터\n라벨 1..N 연속\n얀 굴곡(crimp)이 여기 들어 있음", STEEL],
    [".eld", "요소별 얀 정보", "얀 인덱스\n얀 중심선 상대좌표\n체적분율 · 얀 표면까지 거리", GREEN],
  ];
  const fw = 3.9, fg = 0.24;
  files.forEach((f, i) => {
    const x = M + i * (fw + fg);
    card(s, x, 1.58, fw, 3.28, TINT);
    s.addText(f[0], { x: x + 0.26, y: 1.78, w: fw - 0.52, h: 0.52, fontFace: MONO, fontSize: 26, bold: true, color: f[3], margin: 0 });
    s.addText(f[1], { x: x + 0.26, y: 2.34, w: fw - 0.52, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: INK, margin: 0 });
    s.addText(f[2], { x: x + 0.26, y: 2.72, w: fw - 0.52, h: 1.9, fontFace: KF, fontSize: 11, color: MUTED, margin: 0, valign: "top", lineSpacingMultiple: 1.32 });
  });

  card(s, M, 5.06, CW, 1.34, EMBER_SOFT);
  s.addText("주의", { x: M + 0.3, y: 5.24, w: 0.9, h: 0.3, fontFace: KF, fontSize: 12, bold: true, color: EMBER, margin: 0 });
  s.addText(".ori 는 요소별 데이터라 메쉬와 한 몸이다. 새 메쉬에 옛 .ori 를 쓰면 에러 없이 섬유 방향이 틀린 채로 수렴한다.\n→ 메쉬를 다시 뽑을 때마다 .ori 도 함께 뽑고, 섬유체적비와 얀 평균 방향을 다시 계산한 뒤 쓴다.", {
    x: M + 1.24, y: 5.16, w: CW - 1.56, h: 1.1, fontFace: KF, fontSize: 12, color: INK, margin: 0, valign: "middle", lineSpacingMultiple: 1.25,
  });

  foot(s, "출처 — abaqus/meshes/README.md, abaqus/MESH_REGEN_GUIDE.md", false);
  s.addNotes("이 '조용히 틀리는' 실패 모드가 가장 위험합니다. 그래서 다음 장의 배향 검증을 매번 돌립니다.");
}

// =====================================================================
// 10. 얀 배향 검증
// =====================================================================
{
  const s = sl();
  head(s, "ORIENTATION CHECK", "얀이 제대로 누워 있는가 — 배향 검증", false);

  tbl(s, [
    hdrRow(["검사 항목", "결과", "판정"]),
    [".ori 행 수 vs 요소 수", "26,452 = 26,452 (라벨 1..26452 연속)", "통과"],
    ["방향 누락 요소", "0 개", "통과"],
    ["Yarn0 / Yarn1 평균 방향", "(0.993, 0, ±0.008) → warp ∥ x", "통과"],
    ["Yarn2 / Yarn3 평균 방향", "(0, 0.993, ±0.004) → weft ∥ y", "통과"],
    ["기지 방향", "100 % 단위행렬 (등방성이라 정상)", "통과"],
    ["섬유체적비", "얀 0.4982 × 얀내부 Vf 0.79194 = 39.46 %", "통과"],
    ["RVE 충전율", "메쉬가 박스를 100.0000 % 채움", "통과"],
  ].map((row, i) => i === 0 ? row : [row[0], row[1], { text: row[2], options: { bold: true, color: GREEN } }]),
    M, 1.58, 8.05, [2.85, 4.05, 1.15], { rowH: 0.44 });

  card(s, 9.0, 1.58, 3.71, 2.28, STEEL_SOFT);
  s.addText("0.993 < 1 은 오류가 아니다", { x: 9.24, y: 1.76, w: 3.25, h: 0.56, fontFace: KF, fontSize: 12.5, bold: true, color: STEEL, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("평균 방향벡터 크기가 1보다 작다는 것은 얀이 굴곡(crimp)져 있다는 뜻이다. 평직에서는 정상이며, 오히려 얀이 곧게 펴져 있으면 평직이 아니다.", {
    x: 9.24, y: 2.38, w: 3.25, h: 1.32, fontFace: KF, fontSize: 10.5, color: INK, margin: 0, lineSpacingMultiple: 1.2,
  });

  card(s, 9.0, 4.0, 3.71, 2.14, TINT);
  s.addText("드라이버 매핑", { x: 9.24, y: 4.16, w: 3.25, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  s.addText("0 = e_x    1 = e_y    2 = e_z\n3 = e_xy   4 = e_xz   5 = e_yz", {
    x: 9.24, y: 4.5, w: 3.25, h: 0.66, fontFace: MONO, fontSize: 11, color: EMBER, margin: 0, lineSpacingMultiple: 1.25,
  });
  s.addText("전단 순서를 잘못 알면 G12 와 G13 이 뒤바뀐 채 조용히 수렴한다.", {
    x: 9.24, y: 5.24, w: 3.25, h: 0.74, fontFace: KF, fontSize: 10.5, color: MUTED, margin: 0, lineSpacingMultiple: 1.2,
  });

  card(s, M, 6.14, 8.05, 0.68, GREEN_SOFT);
  s.addText("검증 시점 2026-07-28 · 솔버 없이 텍스트만 읽어서 전부 확인 — coarse 메쉬(26,452 요소) 기준", {
    x: M + 0.28, y: 6.14, w: 7.5, h: 0.68, fontFace: KF, fontSize: 10.5, color: INK, margin: 0, valign: "middle",
  });

  foot(s, "출처 — abaqus/meshes/README.md 검증표", false);
  s.addNotes("이 표의 숫자는 26,452 요소 coarse 메쉬 기준입니다. 174k 생산 메쉬의 검증 숫자는 다음 장들의 PBC 감사 결과입니다.");
}

// =====================================================================
// 11. PBC 왜 필요한가 (dark)
// =====================================================================
{
  const s = sd();
  head(s, "PERIODIC BOUNDARY CONDITIONS", "주기경계조건 — 왜 반드시 필요한가", true);

  card(s, M, 1.58, CW, 1.12, GCARD);
  s.addText([
    { text: "“Since the RVC was used, the periodic boundary conditions should be applied to ensure the\ncompatibility of deformations and continuity of stress.”", options: { italic: true, color: PAPER, fontSize: 12.5 } },
    { text: "   — 논문 §3.2.2", options: { color: EMBER, fontSize: 11 } },
  ], { x: M + 0.32, y: 1.58, w: CW - 0.64, h: 1.12, fontFace: KF, margin: 0, valign: "middle", lineSpacingMultiple: 1.25 });

  const cols = [
    ["자유단으로 두면", ["RVE 표면이 실제로는 이웃 셀에 물려 있는데 자유롭게 벌어진다", "구속이 없으니 강성이 과소평가된다", "마주보는 면에서 응력이 불연속", "셀 크기를 키울수록 답이 계속 바뀐다"], "8E3B24"],
    ["주기경계조건을 걸면", ["마주보는 면의 변위차가 거시 변형률로 고정된다", "변형 적합성 + 응력 연속성이 동시에 만족된다", "셀 하나가 무한 반복 매질을 대표한다", "거시 변형률을 직접 지정하고 거시 응력을 직접 읽을 수 있다"], "2F5568"],
  ];
  const cw2 = 5.9, cg = 0.31;
  cols.forEach((c, i) => {
    const x = M + i * (cw2 + cg);
    card(s, x, 2.94, cw2, 3.0, GCARD);
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.26, y: 3.14, w: 2.6, h: 0.4, fill: { color: c[2] }, rectRadius: 0.05 });
    s.addText(c[0], { x: x + 0.26, y: 3.14, w: 2.6, h: 0.4, fontFace: KF, fontSize: 12, bold: true, color: PAPER, align: "center", valign: "middle", margin: 0 });
    s.addText(c[1].map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < c[1].length - 1 } })), {
      x: x + 0.26, y: 3.66, w: cw2 - 0.52, h: 2.1, fontFace: KF, fontSize: 12, color: ICE, margin: 0, paraSpaceAfter: 8,
    });
  });

  s.addText("논문은 Xia 등의 통일 주기경계조건 [31] 을 인용하고, 파이썬 스크립트로 다점구속(MPC)을 생성했다고만 적었다.\n구속식의 구체적 형태는 논문에 없으므로 우리는 TexGen 이 생성한 Xia 형식을 그대로 쓰고, 그 정합성을 직접 감사했다.", {
    x: M, y: 6.14, w: CW, h: 0.72, fontFace: KF, fontSize: 11.5, color: "9BA4AE", margin: 0, lineSpacingMultiple: 1.25,
  });
  s.addNotes("논문은 PBC를 '적용했다'고만 쓰고 식을 안 줍니다. 그래서 우리 쪽 구속식이 옳다는 것을 스스로 증명해야 했고, 그게 다음 장부터의 검증입니다.");
}

// =====================================================================
// 12. PBC 구현
// =====================================================================
{
  const s = sl();
  head(s, "IMPLEMENTATION", "구현 — *Equation 57식과 드라이버 절점", false);

  card(s, M, 1.58, 6.4, 3.30, GRAPHITE);
  s.addText("구속식", { x: M + 0.3, y: 1.74, w: 3.0, h: 0.28, fontFace: KF, fontSize: 11.5, bold: true, color: EMBER, margin: 0 });
  s.addText("u_slave - u_master = H . d\n\nH = [ e_x   e_xy  e_xz ]\n    [  0    e_y   e_yz ]\n    [  0     0    e_z  ]\n\nFaceA - FaceB - Lx . U_d0 = 0", {
    x: M + 0.3, y: 2.10, w: 5.8, h: 2.50, fontFace: MONO, fontSize: 12.5, color: PAPER, margin: 0, lineSpacingMultiple: 1.18,
  });

  card(s, M, 5.02, 6.4, 1.06, EMBER_SOFT);
  s.addText("→ 드라이버 절점의 변위 U 가 곧 거시 변형률 그 자체가 된다.", {
    x: M + 0.3, y: 5.02, w: 5.8, h: 1.06, fontFace: KF, fontSize: 12.5, bold: true, color: EMBER, margin: 0, valign: "middle",
  });

  const items = [
    ["*Equation 57 식", "마주보는 면의 절점쌍을 격자벡터 하나만큼 묶는다"],
    ["드라이버 절점 6개", "요소에 물리지 않은 순수 DOF 운반체. 6개 거시 변형률 성분을 직접 구동"],
    ["코너 1개 고정", "1/2/3 방향 고정으로 강체모드 억제 — 없으면 강성행렬이 특이해진다"],
    ["세트 순서가 곧 짝짓기", "*Equation 은 나열 순서대로 짝지으므로 정렬하면 깨진다 (TexGen 이 Unsorted 를 붙이는 이유)"],
    ["거시 응력", "σ = RF / V_box — 메쉬 충전율이 100 % 이기 때문에 성립"],
  ];
  let iy = 1.58;
  items.forEach((it, i) => {
    chip(s, i + 1, 7.24, iy + 0.06, i < 2 ? EMBER : STEEL, 0.34);
    s.addText(it[0], { x: 7.72, y: iy, w: 4.99, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: INK, margin: 0 });
    s.addText(it[1], { x: 7.72, y: iy + 0.3, w: 4.99, h: 0.62, fontFace: KF, fontSize: 10.5, color: MUTED, margin: 0, lineSpacingMultiple: 1.16 });
    iy += 1.06;
  });

  foot(s, "출처 — verification/PBC_VALIDATION_GUIDE.md, abaqus/meshes/README.md", false);
  s.addNotes("드라이버 절점 방식의 장점은 거시 변형률을 '지정'하고 거시 응력을 반력에서 '읽는' 것이 대칭적으로 된다는 점입니다.");
}

// =====================================================================
// 13. 검증 4단계
// =====================================================================
{
  const s = sl();
  head(s, "VERIFICATION LADDER", "검증은 사다리다 — 앞이 통과해야 뒤가 의미를 갖는다", false, { ts: 27 });

  const st = [
    ["0", "구속식이 기하학적으로 맞는가", "check_pbc.py", "불필요", "~1 초", EMBER, "통과"],
    ["1", "패치 테스트 — 정답을 아는 문제", "make_pbc_check.py → PBC_PATCH", "필요", "수 분", STEEL, "준비"],
    ["2", "2상 RVE 균질화 (C 행렬 + CTE)", "같은 스크립트 → PBC_ELASTIC", "필요", "수 분", STEEL, "준비"],
    ["3", "EasyPBC 교차검증 (독립 구현)", "make_easypbc_model.py", "필요", "수 분", STEEL, "준비"],
  ];
  let sy = 1.66;
  st.forEach((r) => {
    const passed = r[6] === "통과";
    card(s, M, sy, 12.09, 1.02, passed ? GREEN_SOFT : TINT);
    chip(s, r[0], M + 0.3, sy + 0.29, r[5], 0.44);
    s.addText(r[1], { x: M + 0.98, y: sy + 0.12, w: 4.3, h: 0.4, fontFace: KF, fontSize: 13, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(r[2], { x: M + 0.98, y: sy + 0.52, w: 4.3, h: 0.36, fontFace: MONO, fontSize: 9.5, color: MUTED, valign: "middle", margin: 0 });
    s.addText("Abaqus " + r[3], { x: M + 5.5, y: sy + 0.31, w: 1.75, h: 0.4, fontFace: KF, fontSize: 11, color: MUTED, valign: "middle", margin: 0 });
    s.addText(r[4], { x: M + 7.35, y: sy + 0.31, w: 1.2, h: 0.4, fontFace: KF, fontSize: 11, color: MUTED, valign: "middle", margin: 0 });
    s.addShape(pres.ShapeType.roundRect, { x: M + 10.4, y: sy + 0.31, w: 1.35, h: 0.4, fill: { color: passed ? GREEN : AMBER_SOFT }, rectRadius: 0.05 });
    s.addText(r[6], { x: M + 10.4, y: sy + 0.31, w: 1.35, h: 0.4, fontFace: KF, fontSize: 11, bold: true, color: passed ? PAPER : AMBER, align: "center", valign: "middle", margin: 0 });
    sy += 1.14;
  });

  s.addText("원칙 — 0단계가 깨지면 1단계 이후 숫자는 볼 필요가 없다. check_pbc.py 는 실패 시 exit 1 이므로 파이프라인 게이트로 쓴다.", {
    x: M, y: 6.34, w: CW, h: 0.4, fontFace: KF, fontSize: 11.5, color: EMBER, bold: true, margin: 0, valign: "middle",
  });
  foot(s, "출처 — verification/PBC_VALIDATION_GUIDE.md", false);
  s.addNotes("1~3단계는 스크립트가 다 준비돼 있지만 아직 돌리지 않았습니다. 정직하게 '준비'로 표기했습니다.");
}

// =====================================================================
// 14. 0단계 감사
// =====================================================================
{
  const s = sl();
  head(s, "STAGE 0", "0단계 — 솔버 없이 1초 만에 거르는 7가지", false);

  const checks = [
    "메쉬 / 격자 — 바운딩박스에서 Lx·Ly·Lz, 드라이버가 순수 DOF 운반체인지",
    "세트 페어링 — FaceA[k] 와 FaceB[k] 가 격자벡터 하나만큼 떨어져 있는지",
    "방정식 계수 — 실측 오프셋으로부터 계수를 다시 유도해 파일 값과 대조",
    "DOF 소거 / 과구속 — 소거 DOF 중복, 소거 DOF 에 *Boundary 가 걸렸는지",
    "표면 커버리지 — 모든 표면 절점이 정확히 한 번씩 구속되는지",
    "강체모드 억제 — 코너 하나가 1/2/3 방향으로 고정되어 있는지",
    "부피분율 — tet 부피를 실제로 적분해 박스를 채우는지, 상 분율이 논문과 맞는지",
  ];
  let cy = 1.6;
  checks.forEach((c, i) => {
    chip(s, i + 1, M, cy + 0.03, i < 4 ? EMBER : STEEL, 0.32);
    s.addText(c, { x: M + 0.46, y: cy, w: 7.55, h: 0.38, fontFace: KF, fontSize: 11.5, color: INK, valign: "middle", margin: 0 });
    cy += 0.5;
  });

  card(s, 8.7, 1.58, 4.01, 1.06, GREEN);
  s.addText("RESULT: PBC DEFINITION\nIS CONSISTENT", { x: 8.7, y: 1.66, w: 4.01, h: 0.6, fontFace: MONO, fontSize: 12, bold: true, color: PAPER, align: "center", margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("6개 덱 전부 · 경고 0 건", { x: 8.7, y: 2.24, w: 4.01, h: 0.3, fontFace: KF, fontSize: 10.5, color: "C8E0D3", align: "center", margin: 0 });

  const nums = [
    ["V_RVE", "5.390000 mm³"],
    ["충전율", "100.0000 %"],
    ["방정식", "57 식 전부 정합"],
    ["표면 절점", "9,062 (면 8,630 · 모서리 424 · 꼭짓점 8)"],
    ["대응 절점 수", "x 394=394 · y 406=406 · z 3951=3951"],
    ["상 분율", "얀 50.51 % / 기지 49.49 %"],
    ["전체 Vf", "0.5051 × 0.792 = 0.4000"],
  ];
  card(s, 8.7, 2.76, 4.01, 3.34, TINT);
  let ny = 2.94;
  nums.forEach((n) => {
    s.addText(n[0], { x: 8.94, y: ny, w: 1.10, h: 0.44, fontFace: KF, fontSize: 10, bold: true, color: STEEL, valign: "middle", margin: 0 });
    s.addText(n[1], { x: 10.06, y: ny, w: 2.5, h: 0.44, fontFace: KF, fontSize: 9, color: INK, valign: "middle", margin: 0 });
    ny += 0.45;
  });

  card(s, M, 5.28, 8.05, 0.82, EMBER_SOFT);
  s.addText("마주보는 면의 절점 수가 정확히 같다 = 메쉬 자체가 주기적이다. 다르면 TexGen 에서 다시 뽑아야 한다.", {
    x: M + 0.28, y: 5.28, w: 7.5, h: 0.82, fontFace: KF, fontSize: 11.5, color: INK, margin: 0, valign: "middle", lineSpacingMultiple: 1.15,
  });

  foot(s, "출처 — verification/check_pbc.py 실행 결과 (PBC_VALIDATION_GUIDE.md 기재) · 174,405 요소 생산 덱 기준", false);
  s.addNotes("Vf 0.4000이 여기서 다시 확인됩니다. 얀 체적분율 50.51%에 얀 내부 섬유분율 0.792를 곱한 값입니다.");
}

// =====================================================================
// 15. 결함 11종 주입
// =====================================================================
{
  const s = sl();
  head(s, "TESTING THE TESTER", "통과만 하는 검사기는 쓸모없다", false);

  s.addText("정상 덱에 실제로 자주 나는 결함 11가지를 일부러 주입해서, 감사 도구가 전부 잡아내는지 확인했다.", {
    x: M, y: 1.42, w: CW, h: 0.36, fontFace: KF, fontSize: 13, color: INK, margin: 0, valign: "middle",
  });

  const faults = [
    "옛날 격자길이", "면 세트 길이 불일치", "세트 순서 뒤바뀜", "전단항 삭제",
    "부호 반전", "DOF 이중 소거", "소거 DOF 에 *Boundary", "코너 고정 삭제",
    "표면 절점 누락", "드라이버 번호 충돌", "비주기 메쉬",
  ];
  const fw2 = 2.85, fh = 0.62, fgx = 0.24, fgy = 0.22;
  faults.forEach((f, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = M + col * (fw2 + fgx), y = 2.0 + row * (fh + fgy);
    card(s, x, y, fw2, fh, TINT, "DCE0E5");
    s.addText("✕", { x: x + 0.16, y, w: 0.3, h: fh, fontFace: KF, fontSize: 12, bold: true, color: EMBER, valign: "middle", align: "center", margin: 0 });
    s.addText(f, { x: x + 0.5, y, w: fw2 - 0.66, h: fh, fontFace: KF, fontSize: 11, color: INK, valign: "middle", margin: 0 });
  });

  card(s, 9.2, 4.52, 3.51, 0.62, GREEN);
  s.addText("ALL 11 FAULTS DETECTED", { x: 9.2, y: 4.52, w: 3.51, h: 0.62, fontFace: MONO, fontSize: 12, bold: true, color: PAPER, align: "center", valign: "middle", margin: 0 });

  card(s, M, 5.46, CW, 1.14, GRAPHITE);
  s.addText([
    { text: "왜 이걸 하는가.  ", options: { bold: true, color: EMBER, fontSize: 13 } },
    { text: "감사 도구가 “통과”라고 말했을 때 그 말을 믿을 근거가 있어야 하기 때문이다. 잡지 못하는 검사는 통과와 구별되지 않는다.", options: { color: PAPER, fontSize: 13 } },
  ], { x: M + 0.32, y: 5.46, w: CW - 0.64, h: 1.14, fontFace: KF, margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });

  foot(s, "출처 — verification/test_check_pbc.py", false);
  s.addNotes("이 슬라이드는 '검증의 검증'입니다. 질문이 나오면 실제 주입 코드가 리포에 있다고 답하세요.");
}

// =====================================================================
// 16. 1~3단계
// =====================================================================
{
  const s = sl();
  head(s, "STAGE 1–3", "1~3단계 — 준비된 검증, 아직 돌리지 않은 것", false);

  const stages = [
    ["1  패치 테스트", "RVE 전체에 등방 재료 하나만 넣고 거시 변형률을 건다. 정답이 닫힌 형태로 알려져 있다.\n\nC3D4 는 상수변형률을 정확히 표현하므로 판정 기준이 “그럴듯한가”가 아니라 “1e-12 인가”가 된다.", EMBER],
    ["2  2상 균질화", "손상·소성을 뺀 선형 탄성 2상 RVE.\n\n6×6 강성 C, 공학상수 9개, 균질화 CTE 를 얻고 평균화 · Hill–Mandel · 대칭성 3가지가 독립적으로 검증된다.", STEEL],
    ["3  EasyPBC 교차검증", "EasyPBC (Omairey et al., SoftwareX 9, 2019) 는 자기 구속식을 따로 만든다. 우리 코드와 한 줄도 공유하지 않는 독립 구현.\n\n같은 메쉬에서 같은 답이면 외부 확증.", GREEN],
  ];
  const sw = 3.9, sg = 0.24;
  stages.forEach((st, i) => {
    const x = M + i * (sw + sg);
    card(s, x, 1.58, sw, 2.98, TINT);
    s.addText(st[0], { x: x + 0.26, y: 1.76, w: sw - 0.52, h: 0.34, fontFace: KF, fontSize: 13.5, bold: true, color: st[2], margin: 0 });
    s.addText(st[1], { x: x + 0.26, y: 2.20, w: sw - 0.52, h: 2.20, fontFace: KF, fontSize: 10.5, color: INK, margin: 0, valign: "top", lineSpacingMultiple: 1.24 });
  });

  s.addText("패치 테스트 통과 기준", { x: M, y: 4.74, w: 6.5, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  tbl(s, [
    hdrRow(["항목", "기준"]),
    ["응력장 균일성", "peak-to-peak / |σ| < 1e-6"],
    ["주기 요동 u − H·x", "퍼짐 / (H·L) < 1e-6"],
    ["C = C_isotropic", "상대오차 < 1e-6"],
    ["균질화 CTE", "상대오차 < 1e-4"],
  ], M, 5.1, 6.5, [3.0, 3.5], { rowH: 0.32, fs: 10.5 });

  card(s, 7.4, 4.74, 5.31, 1.98, AMBER_SOFT);
  s.addText("정직하게 밝힐 것", { x: 7.68, y: 4.9, w: 4.75, h: 0.3, fontFace: KF, fontSize: 12.5, bold: true, color: AMBER, margin: 0 });
  s.addText("1~3단계 스크립트는 전부 작성돼 있으나, 실행 결과는 현재 자료에 없다. 즉 이 세 단계는 “통과”라고 말할 수 없다.\n\n다만 PBC 가 옳다는 증거는 다른 경로로 이미 확보되어 있다 → 다음 장.", {
    x: 7.68, y: 5.24, w: 4.75, h: 1.34, fontFace: KF, fontSize: 11, color: INK, margin: 0, valign: "top", lineSpacingMultiple: 1.24,
  });

  foot(s, "출처 — verification/PBC_VALIDATION_GUIDE.md 1~3단계", false);
  s.addNotes("여기서 질문이 나올 수 있습니다. '왜 안 돌렸나' → 본해석에서 이미 더 강한 증거가 나왔기 때문에 우선순위가 밀렸다고 답하고 다음 장으로 넘어가세요.");
}

// =====================================================================
// 17. 확보된 PBC 증거
// =====================================================================
{
  const s = sl();
  head(s, "EVIDENCE", "그래도 PBC는 이미 증명됐다 — 본해석에서 나온 네 가지", false);

  const ev = [
    ["드라이버 반력", "6개 전부 0", "구속이 새지 않는다", EMBER],
    ["체적가중 평균응력 잔차", "4.0e−8", "기계정밀도 수준", STEEL],
    ["횡방향 응력", "전 증분 0.000", "단축 인장이 정확히 단축", STEEL],
    ["강성 6×6 대칭성 위반", "0.0000 %", "PBC 와 야코비안이 동시에 옳아야만 나온다", GREEN],
  ];
  const ew = 2.94, eg = 0.19;
  ev.forEach((e, i) => {
    const x = M + i * (ew + eg);
    card(s, x, 1.58, ew, 2.7, TINT);
    s.addText(e[0], { x: x + 0.24, y: 1.78, w: ew - 0.48, h: 0.56, fontFace: KF, fontSize: 11, bold: true, color: MUTED, margin: 0, lineSpacingMultiple: 1.1 });
    s.addText(e[1], { x: x + 0.24, y: 2.4, w: ew - 0.48, h: 0.72, fontFace: KF, fontSize: 21, bold: true, color: e[3], margin: 0, valign: "middle" });
    s.addText(e[2], { x: x + 0.24, y: 3.2, w: ew - 0.48, h: 0.84, fontFace: KF, fontSize: 10.5, color: INK, margin: 0, lineSpacingMultiple: 1.2 });
  });

  card(s, M, 4.46, CW, 1.28, GREEN_SOFT);
  s.addText([
    { text: "네 번째가 가장 강하다. ", options: { bold: true, color: GREEN, fontSize: 13.5 } },
    { text: "추출 과정에서 대칭을 강제하는 부분이 전혀 없는데도 C_ij 와 C_ji 가 0.0000 % 로 같다는 것은, 주기경계조건과 UMAT 할선 야코비안이 ", options: { color: INK, fontSize: 13.5 } },
    { text: "동시에", options: { bold: true, color: INK, fontSize: 13.5 } },
    { text: " 옳아야만 나오는 값이다.", options: { color: INK, fontSize: 13.5 } },
  ], { x: M + 0.32, y: 4.46, w: CW - 0.64, h: 1.28, fontFace: KF, margin: 0, valign: "middle", lineSpacingMultiple: 1.22 });

  s.addText("여전히 남은 것 — 패치 테스트 · EasyPBC 교차검증은 미실행. RVE 수준 메쉬 수렴성도 미검증.", {
    x: M, y: 5.94, w: CW, h: 0.38, fontFace: KF, fontSize: 11.5, color: AMBER, bold: true, margin: 0, valign: "middle",
  });

  foot(s, "출처 — 랩미팅 브리프 §7 (예상질문), §4.5 손상 후 균질화 강성", false);
  s.addNotes("'PBC 제대로 걸렸냐'는 질문에 대한 준비된 답이 이 장입니다. 네 개 중 마지막 하나만 말해도 충분합니다.");
}

// =====================================================================
// 18. 넣고 나서
// =====================================================================
{
  const s = sl();
  head(s, "AFTER THE RVE", "RVE를 넣고 나서 — 조립과 해석 절차", false);

  s.addText("① 조립 — assemble_inp.py", { x: M, y: 1.5, w: 5.9, h: 0.32, fontFace: KF, fontSize: 13, bold: true, color: EMBER, margin: 0 });
  const asm = [
    ["입력", "TexGen 메쉬 (.inp + .ori + .eld)"],
    ["교체", "TexGen 이 붙인 재료 · 스텝은 버리고 UMAT 카드로 교체"],
    ["재료명", "SIC_MATRIX_DAMAGE / CSIC_YARN_DAMAGE (CMNAME 검사)"],
    ["얀 물성", "Chamis(강성) · Schapery(CTE) 미시역학 — 오차 0.005 % 이내"],
    ["출력", "3온도 덱 (RT23 / T500 / T1000) · double precision 필수"],
  ];
  let ay = 1.9;
  asm.forEach((a) => {
    s.addText(a[0], { x: M, y: ay, w: 0.98, h: 0.44, fontFace: KF, fontSize: 10.5, bold: true, color: STEEL, valign: "middle", margin: 0 });
    s.addText(a[1], { x: M + 1.02, y: ay, w: 4.88, h: 0.44, fontFace: KF, fontSize: 11, color: INK, valign: "middle", margin: 0 });
    ay += 0.48;
  });

  s.addText("② 해석 절차 — 논문 §3.2.4 와 동일", { x: 6.9, y: 1.5, w: 5.81, h: 0.32, fontFace: KF, fontSize: 13, bold: true, color: EMBER, margin: 0 });
  const steps = [
    ["Step 1", "냉각", "1050 °C → 23 °C · 잔류응력과 초기 손상", EMBER],
    ["Step 2", "승온", "23 °C → 시험온도 · 응력 재분배", EMBER],
    ["Step 3", "인장", "시험온도 유지 · 주기경계 x 방향 인장", EMBER],
    ["Step 4–9", "추가", "HOM_E11 ~ HOM_G23 선형섭동 6스텝", STEEL],
  ];
  let ty = 1.9;
  steps.forEach((st) => {
    card(s, 6.9, ty, 5.81, 0.76, st[3] === EMBER ? TINT : STEEL_SOFT);
    s.addText(st[0], { x: 7.12, y: ty, w: 0.95, h: 0.76, fontFace: KF, fontSize: 11, bold: true, color: st[3], valign: "middle", margin: 0 });
    s.addText(st[1], { x: 8.05, y: ty, w: 0.72, h: 0.76, fontFace: KF, fontSize: 12, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(st[2], { x: 8.8, y: ty, w: 3.7, h: 0.76, fontFace: KF, fontSize: 10.5, color: MUTED, valign: "middle", margin: 0 });
    ty += 0.84;
  });

  card(s, 6.9, 5.3, 5.81, 1.1, GREEN_SOFT);
  s.addText("Step 4–9 는 논문에 없다. 같은 해석 안에서 손상 후 균질화 강성 6×6 을 새 해석 없이 뽑기 위해 우리가 붙인 것이다.", {
    x: 7.12, y: 5.3, w: 5.37, h: 1.1, fontFace: KF, fontSize: 11, color: INK, margin: 0, valign: "middle", lineSpacingMultiple: 1.2,
  });

  card(s, M, 4.42, 5.9, 1.98, GRAPHITE);
  s.addText("메쉬가 바뀌어도 재료카드와 스텝은 그대로 재사용된다", { x: M + 0.28, y: 4.6, w: 5.34, h: 0.56, fontFace: KF, fontSize: 12.5, bold: true, color: EMBER, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("크랙밴드 정규화가 요소크기를 흡수하기 때문이다. 그래서 coarse 메쉬로 경향을 먼저 보고, 같은 카드로 조밀 메쉬를 돌릴 수 있다.", {
    x: M + 0.28, y: 5.2, w: 5.34, h: 1.06, fontFace: KF, fontSize: 11, color: ICE, margin: 0, lineSpacingMultiple: 1.22,
  });

  foot(s, "출처 — abaqus/assemble_inp.py, MESH_REGEN_GUIDE.md, 논문 §3.2.4, 브리프 §3.3", false);
  s.addNotes("논문 3스텝을 그대로 따라갑니다. 6개 섭동 스텝만 우리가 추가한 것이고, 이건 논문에 없는 정보를 공짜로 얻는 장치입니다.");
}

// =====================================================================
// 19. 결과 & 다음 (dark)
// =====================================================================
{
  const s = sd();
  head(s, "WHERE IT STANDS", "여기까지의 결과, 그리고 다음", true);

  s.addText("인장강도 — 논문 절차(23 °C 경유) 기준", { x: M, y: 1.5, w: 6.6, h: 0.32, fontFace: KF, fontSize: 12.5, bold: true, color: EMBER, margin: 0 });
  s.addTable([
    ["온도", "우리 모델", "논문 해석", "차이"].map((t) => ({ text: t, options: { bold: true, color: PAPER, fill: { color: "3F4650" }, fontSize: 11 } })),
    [{ text: "23 °C", options: { color: PAPER } }, { text: "125.81 MPa", options: { color: PAPER, bold: true } }, { text: "128.45", options: { color: ICE } }, { text: "−2.1 %", options: { color: "6FBF8F", bold: true } }],
    [{ text: "500 °C", options: { color: PAPER } }, { text: "129.23", options: { color: PAPER, bold: true } }, { text: "179.42", options: { color: ICE } }, { text: "−28.0 %", options: { color: "E8845F", bold: true } }],
    [{ text: "1000 °C", options: { color: PAPER } }, { text: "122.19", options: { color: PAPER, bold: true } }, { text: "199.15", options: { color: ICE } }, { text: "−38.6 %", options: { color: "E8845F", bold: true } }],
  ], {
    x: M, y: 1.88, w: 6.6, colW: [1.4, 1.85, 1.65, 1.7], rowH: 0.42,
    fontFace: KF, fontSize: 11.5, fill: { color: GCARD },
    border: { type: "solid", color: "4A515B", pt: 1 }, align: "left", valign: "middle", margin: 0.07,
  });

  card(s, M, 3.86, 6.6, 1.42, "3A2C25");
  s.addText([
    { text: "먼저 밝힐 것 — ", options: { bold: true, color: EMBER, fontSize: 12 } },
    { text: "23 °C 의 125.81 MPa 는 얀 종방향 강도 X_y,1t = 421 MPa 를 논문 Table 3 에 맞춰 역보정해서 얻은 값이다. 예측이 아니라 보정이다.", options: { color: PAPER, fontSize: 12 } },
  ], { x: M + 0.3, y: 3.86, w: 6.0, h: 1.42, fontFace: KF, margin: 0, valign: "middle", lineSpacingMultiple: 1.22 });

  s.addText("다음에 할 것", { x: 7.9, y: 1.5, w: 4.81, h: 0.32, fontFace: KF, fontSize: 12.5, bold: true, color: EMBER, margin: 0 });
  const next = [
    ["PAPERFAITH 체인", "논문 절차로 돌아가되 냉각 손상을 논문 수준까지. 링크당 변수 하나만 — P0/P1/P2 실행 중"],
    ["Fig. 4 로 판정", "기지 손상 개시온도와 도달률로 합격 여부를 가른다"],
    ["패치 테스트 · EasyPBC", "PBC 검증 사다리 1~3단계 실행"],
    ["메쉬 수렴성", "V2_6 얀 크랙밴드 정규화 이후에만 의미가 있다"],
  ];
  let ny2 = 1.9;
  next.forEach((n, i) => {
    chip(s, i + 1, 7.9, ny2 + 0.05, i < 2 ? EMBER : STEEL, 0.34);
    s.addText(n[0], { x: 8.38, y: ny2, w: 4.33, h: 0.3, fontFace: KF, fontSize: 12, bold: true, color: PAPER, margin: 0 });
    s.addText(n[1], { x: 8.38, y: ny2 + 0.3, w: 4.33, h: 0.74, fontFace: KF, fontSize: 10.5, color: ICE, margin: 0, lineSpacingMultiple: 1.18 });
    ny2 += 1.16;
  });

  card(s, M, 5.5, 6.6, 1.18, GCARD);
  s.addText("형상과 경계조건은 논쟁의 대상이 아니다.\n남은 문제는 전부 손상 물리 쪽에 있다.", {
    x: M + 0.3, y: 5.5, w: 6.0, h: 1.18, fontFace: KF, fontSize: 13.5, bold: true, color: PAPER, margin: 0, valign: "middle", lineSpacingMultiple: 1.22,
  });

  foot(s, "출처 — 랩미팅 브리프 §4.1 · §6.1 · §8 · verification/PAPER_DEVIATION_REGISTER.md", true);
  s.addNotes("고온이 안 맞는 이유(비가역 손상 + 상온 경유, 잔류응력 크기 부족)는 다음 회차 주제입니다. 오늘은 여기까지만 예고합니다.");
}

pres.writeFile({ fileName: F("CSiC_RVE_labmeeting_0806.pptx") }).then((f) => console.log("WROTE", f));
