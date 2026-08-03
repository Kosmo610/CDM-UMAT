"""CSIC UMAT 물성 대장 (Zhang 2022 재현용) 엑셀 생성."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

F = 'Arial'
H_FILL = PatternFill('solid', fgColor='1F3864')
CAT_FILL = PatternFill('solid', fgColor='D9E2F3')
OK_FILL = PatternFill('solid', fgColor='E2EFDA')   # 검증완료
CAL_FILL = PatternFill('solid', fgColor='FFF2CC')  # 보정값
TMP_FILL = PatternFill('solid', fgColor='FCE4D6')  # 임시값
NG_FILL = PatternFill('solid', fgColor='F8CBAD')   # 미검증
NUM_FILL = PatternFill('solid', fgColor='F2F2F2')  # 수치설정
THIN = Side(style='thin', color='BFBFBF')
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

STATUS_FILL = {'검증완료': OK_FILL, '보정값': CAL_FILL, '임시값': TMP_FILL,
               '미검증': NG_FILL, '수치설정': NUM_FILL}

PAPER = 'Zhang et al. 2022, Ceram. Int. 48:3109-3124'

# 구분, 이름, 기능, 값, 단위, 출처, 상태, 비고
ROWS = [
    ('A. T300 섬유 (논문 Table 1)', None, None, None, None, None, None, None),
    ('A', 'Ef1', '섬유 축(1)방향 탄성계수', 230.0, 'GPa', PAPER + ' Table 1 [34,35]', '검증완료', '논문 직접 인용'),
    ('A', 'Ef2', '섬유 횡(2,3)방향 탄성계수', 40.0, 'GPa', PAPER + ' Table 1', '검증완료', '논문 직접 인용'),
    ('A', 'Gf12', '섬유 면내 전단탄성계수', 24.0, 'GPa', PAPER + ' Table 1', '검증완료', '논문 직접 인용'),
    ('A', 'Gf23', '섬유 횡방향 전단탄성계수', 14.3, 'GPa', PAPER + ' Table 1', '검증완료', '논문 직접 인용'),
    ('A', 'nu_f12', '섬유 주 포아송비', 0.26, '-', PAPER + ' Table 1', '검증완료', '논문 직접 인용'),
    ('A', 'Xf,t', '섬유 축방향 인장강도', 3580.0, 'MPa', PAPER + ' Table 1', '검증완료', '얀 강도 환산의 상한 기준'),
    ('A', 'Xf,c', '섬유 축방향 압축강도', 2470.0, 'MPa', PAPER + ' Table 1', '검증완료', '논문 직접 인용'),
    ('A', 'alpha_f1', '섬유 축방향 열팽창계수', -0.3e-6, '1/K', PAPER + ' Table 1', '검증완료', '음수. 기지와의 불일치가 잔류응력 원인'),
    ('A', 'alpha_f2(3)', '섬유 횡방향 열팽창계수', 3.1e-6, '1/K', PAPER + ' Table 1', '검증완료', '논문 직접 인용'),

    ('B. SiC 기지 (논문 Table 2)', None, None, None, None, None, None, None),
    ('B', 'Em', '기지 탄성계수', 350.0, 'GPa', PAPER + ' Table 2 [35-37]', '검증완료', '논문 직접 인용'),
    ('B', 'Gm', '기지 전단탄성계수', 146.0, 'GPa', PAPER + ' Table 2', '검증완료', 'E/(2(1+nu))=145.83 과 0.11% 일치 (자기무모순 확인)'),
    ('B', 'nu_m', '기지 포아송비', 0.20, '-', PAPER + ' Table 2', '검증완료', '논문 직접 인용'),
    ('B', 'Xm,t(c)', '기지 인장=압축 강도', 310.0, 'MPa', PAPER + ' Table 2', '검증완료', '논문이 인장·압축에 같은 값 하나만 제시'),
    ('B', 'alpha_m', '기지 열팽창계수', 4.5e-6, '1/K', PAPER + ' Table 2', '검증완료', '온도무관 상수 (논문 3.2.3)'),

    ('C. RVE 형상 · 체적분율', None, None, None, None, None, None, None),
    ('C', 'Lx', 'RVE x 방향 치수', 3.5, 'mm', PAPER + ' 3.2.1', '검증완료', '논문과 동일'),
    ('C', 'Ly', 'RVE y 방향 치수', 3.5, 'mm', PAPER + ' 3.2.1', '검증완료', '논문과 동일'),
    ('C', 'Lz', 'RVE 두께', 0.44, 'mm', '자체 TexGen 모델', '미검증', '논문은 0.4334 mm. 1.5% 차이 (영향 경미로 판단)'),
    ('C', '타원 장축', '얀 단면 타원 장축', 1.28, 'mm', PAPER + ' 3.2.1', '검증완료', '논문과 동일'),
    ('C', '타원 단축', '얀 단면 타원 단축', 0.20, 'mm', PAPER + ' 3.2.1', '검증완료', '논문과 동일'),
    ('C', 'V_RVE', 'RVE 총 체적', 5.390000, 'mm^3', '메쉬 적분 (자체 검증)', '검증완료', '3.5 x 3.5 x 0.44 와 정확히 일치'),
    ('C', 'Vf_tow', '얀 내부 섬유체적분율', 0.79194, '-', '얀 물성 역산 (논문 미기재)', '검증완료', '이 값에서 전체 Vf=0.400 이 재현됨'),
    ('C', 'V_tow/V_RVE', '얀(tow) 체적분율', 0.5051, '-', '메쉬 적분', '검증완료', '자체 계산'),
    ('C', 'Vf_total', '전체 섬유체적분율', 0.400, '-', '0.79194 x 0.5051', '검증완료', '논문 명시값 40% 와 정확히 일치'),
    ('C', 'N_elem', 'C3D4 요소 개수', 174405, '개', '자체 TexGen 메쉬', '미검증', '논문은 116,724개. 1.5배 조밀 (메쉬수렴성 미검증)'),

    ('D. 얀 균질화 물성 (Chamis / Schapery)', None, None, None, None, None, None, None),
    ('D', 'Ey1', '얀 축방향 탄성계수', 254967.228042, 'MPa', 'Chamis 혼합법칙 [32]', '검증완료', '재계산 오차 -0.000011%'),
    ('D', 'Ey2', '얀 횡방향 탄성계수', 44321.737572, 'MPa', 'Chamis [32]', '검증완료', '재계산 오차 -0.000013%'),
    ('D', 'Ey3', '얀 횡방향 탄성계수', 44321.737572, 'MPa', '= Ey2 (횡등방)', '검증완료', '횡등방성 가정'),
    ('D', 'nu_y12', '얀 주 포아송비', 0.247516386, '-', 'Chamis 혼합법칙', '검증완료', '재계산 오차 +0.000006%'),
    ('D', 'nu_y13', '얀 주 포아송비', 0.247516386, '-', '= nu_y12', '검증완료', '횡등방성 가정'),
    ('D', 'nu_y23', '얀 횡방향 포아송비', 0.395813581, '-', 'Ey2/(2Gy23)-1', '검증완료', '재계산 오차 +0.0048%'),
    ('D', 'Gy12', '얀 면내 전단탄성계수', 26431.515264, 'MPa', 'Chamis [32]', '검증완료', '재계산 오차 -0.0023%'),
    ('D', 'Gy13', '얀 면내 전단탄성계수', 26431.515264, 'MPa', '= Gy12', '검증완료', '횡등방성 가정'),
    ('D', 'Gy23', '얀 횡방향 전단탄성계수', 15876.667974, 'MPa', 'Chamis [32]', '검증완료', '재계산 오차 -0.0014%'),
    ('D', 'alpha_y1', '얀 축방향 열팽창계수', 1.070925962822e-6, '1/K', 'Schapery 혼합법칙 [33]', '검증완료', '재계산 오차 -0.00013%'),
    ('D', 'alpha_y2', '얀 횡방향 열팽창계수', 3.324908565604e-6, '1/K', 'Chamis CTE 식', '검증완료', '재계산 오차 -0.000007%'),
    ('D', 'alpha_y3', '얀 횡방향 열팽창계수', 3.324908565604e-6, '1/K', '= alpha_y2', '검증완료', '횡등방성 가정'),

    ('E. 기지 UMAT 카드 (SIC_MATRIX_DAMAGE, constants=23~24)', None, None, None, None, None, None, None),
    ('E', 'PROPS 1', '재료 분기 플래그 (2=기지)', 2.0, '-', 'UMAT 내부 규약', '수치설정', '물성 아님'),
    ('E', 'PROPS 2  E', '기지 탄성계수', 350000.0, 'MPa', PAPER + ' Table 2', '검증완료', '논문값 350 GPa'),
    ('E', 'PROPS 3  NU', '기지 포아송비', 0.20, '-', PAPER + ' Table 2', '검증완료', '논문값'),
    ('E', 'PROPS 4  XT', '기지 인장강도 (Weibull 평균)', 310.0, 'MPa', PAPER + ' Table 2', '검증완료', '요소별 Weibull 샘플링의 평균. 실측 310.093 (오차 0.030%)'),
    ('E', 'PROPS 5  XC', '기지 압축강도', 310.0, 'MPa', PAPER + ' Table 2', '검증완료', '초기 900 -> 논문값 310 으로 수정 완료'),
    ('E', 'PROPS 6  AT', '인장 손상진화 지수', 2.0, '-', '논문 미기재', '임시값', 'Gf>0 이면 크랙밴드 A_eff 로 덮어써짐'),
    ('E', 'PROPS 7  AC', '압축 손상진화 지수', 2.0, '-', '논문 미기재', '임시값', '미보정'),
    ('E', 'PROPS 8  DMAXT', '인장 손상 상한', 0.95, '-', '논문 미기재', '임시값', '최대점 이후 비물리적 재상승의 원인'),
    ('E', 'PROPS 9  DMAXC', '압축 손상 상한', 0.80, '-', '논문 미기재', '임시값', '미보정'),
    ('E', 'PROPS 10 ETA', '점성 정규화 시간상수', 0.02, 'step time', '자체 수렴검사로 선정', '수치설정', '1.0x/0.5x/0.25x 검사 -> 0.5x 에서 강성 수렴 (0.87%)'),
    ('E', 'PROPS 11 DJMAX', '증분당 손상 점프 상한', 0.10, '-', '수치안정용', '수치설정', '물성 아님'),
    ('E', 'PROPS 12 FREEZESTEP', '손상이 살아있는 마지막 Step', 3.0, '-', '해석 절차 설정', '수치설정', '냉각1+승온2+인장3. HOM Step(4~9)은 동결'),
    ('E', 'PROPS 13 CLOSURE', '균열닫힘 강성회복 계수', 0.05, '-', '논문 미기재', '임시값', '미보정'),
    ('E', 'PROPS 14 PMIN', 'PNEWDT 하한', 0.25, '-', '수치안정용', '수치설정', '물성 아님'),
    ('E', 'PROPS 15 ENABLE', '손상 on/off 스위치', 1.0, '-', '해석 설정', '수치설정', '무손상 기준해석시 0'),
    ('E', 'PROPS 16 GFT', '기지 파괴에너지 (크랙밴드)', 0.018, 'N/mm', '논문 미기재', '임시값', '요소크기 정규화용. 0.031->0.012->0.018 로 조정된 이력'),
    ('E', 'PROPS 17 WEIBM', 'Weibull 형상모수 m', 5.1, '-', '논문 미기재', '임시값', '강도 산포 도입 (논문은 결정론적)'),
    ('E', 'PROPS 18 SEED', 'Weibull 해시 시드', 1.0, '-', '재현성 확보용', '수치설정', '좌표 해시 기반 결정론적'),
    ('E', 'PROPS 19 CUTTRG', '컷백 트리거 배수', 1.15, '-', '수치안정용', '수치설정', '물성 아님'),
    ('E', 'PROPS 20 CUTSAF', '컷백 안전계수', 0.75, '-', '수치안정용', '수치설정', '물성 아님'),
    ('E', 'PROPS 21 CUTMXF', '컷백 최대 감쇠', 0.50, '-', '수치안정용', '수치설정', '물성 아님'),
    ('E', 'PROPS 22 I1GATE', '제1불변량 게이트 모드', 1.0, '-', PAPER + ' Eq.16', '검증완료', '논문 Eq.16 의 I1<=0 조건 구현'),
    ('E', 'PROPS 23 WTLAG', '응력상태가중 1증분 지연', 1.0, '-', '야코비안 일관성 확보', '수치설정', 'V2_4 발산 수정. 재료점 오차 7.36%->0.00%'),
    ('E', 'PROPS 24 MCRIT', '기지 파손기준 선택 (V2_5)', 1.0, '-', PAPER + ' Eq.15/16', '검증완료', 'PAPERCRIT 덱만. 1=논문 von Mises, 0=Rankine(V2_4)'),

    ('F. 얀 UMAT 카드 (CSIC_YARN_DAMAGE, constants=31)', None, None, None, None, None, None, None),
    ('F', 'PROPS 1', '재료 분기 플래그 (1=얀)', 1.0, '-', 'UMAT 내부 규약', '수치설정', '물성 아님'),
    ('F', 'PROPS 2~10', '얀 직교이방 탄성상수 9개', None, 'MPa / -', 'Chamis 균질화 (구분 D 참조)', '검증완료', 'E1,E2,E3,nu12,nu13,nu23,G12,G13,G23'),
    ('F', 'PROPS 11 XT', '얀 축방향 인장강도', 421.0, 'MPa', '논문 Table 3 역보정 (논문 미기재)', '보정값', '★핵심 보정값. Chamis 이론값 2835 MPa 의 14.8%'),
    ('F', 'PROPS 12 XC', '얀 축방향 압축강도', 1500.0, 'MPa', '논문 미기재', '임시값', '미보정. 냉각 압축(-355MPa)에 여유 있어 영향 작음'),
    ('F', 'PROPS 13 YT', '얀 횡방향 인장강도', 80.0, 'MPa', '논문 미기재', '임시값', '미보정. 횡손상률 88~93% 결정'),
    ('F', 'PROPS 14 YC', '얀 횡방향 압축강도', 350.0, 'MPa', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 15 S12', '면내 전단강도', 120.0, 'MPa', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 16 S13', '면외 전단강도', 120.0, 'MPa', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 17 S23', '횡방향 전단강도', 100.0, 'MPa', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 18 A1T', '축방향 인장 손상진화 지수', 2.0, '-', '논문 미기재', '임시값', '★크랙밴드(Gf) 정규화 없음 -> eta·메쉬 의존의 근본원인'),
    ('F', 'PROPS 19 A1C', '축방향 압축 손상진화 지수', 2.0, '-', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 20 ATT', '횡방향 인장 손상진화 지수', 2.0, '-', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 21 ATC', '횡방향 압축 손상진화 지수', 2.0, '-', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 22 DMAX1', '축방향 손상 상한', 0.95, '-', '논문 미기재', '임시값', '미보정'),
    ('F', 'PROPS 23 DMAXT', '횡방향 손상 상한', 0.90, '-', '논문 미기재', '임시값', '최대점 이후 재상승 원인 중 하나'),
    ('F', 'PROPS 24 ETA', '점성 정규화 시간상수', 0.01, 'step time', '자체 수렴검사로 선정', '수치설정', '기지 ETA 의 절반으로 유지'),
    ('F', 'PROPS 25 DJMAX', '증분당 손상 점프 상한', 0.10, '-', '수치안정용', '수치설정', '물성 아님'),
    ('F', 'PROPS 26 FREEZESTEP', '손상이 살아있는 마지막 Step', 3.0, '-', '해석 절차 설정', '수치설정', '기지 PROPS12 와 동일해야 함'),
    ('F', 'PROPS 27 PMIN', 'PNEWDT 하한', 0.25, '-', '수치안정용', '수치설정', '물성 아님'),
    ('F', 'PROPS 28 ENABLE', '손상 on/off 스위치', 1.0, '-', '해석 설정', '수치설정', '무손상 기준해석시 0'),
    ('F', 'PROPS 29 CUTTRG', '컷백 트리거 배수', 1.15, '-', '수치안정용', '수치설정', '물성 아님'),
    ('F', 'PROPS 30 CUTSAF', '컷백 안전계수', 0.75, '-', '수치안정용', '수치설정', '물성 아님'),
    ('F', 'PROPS 31 CUTMXF', '컷백 최대 감쇠', 0.50, '-', '수치안정용', '수치설정', '물성 아님'),

    ('G. 해석 조건', None, None, None, None, None, None, None),
    ('G', 'T_process', '공정(무응력) 온도', 1050.0, 'degC', PAPER + ' 3.2.4 / *Expansion zero', '검증완료', '논문과 동일'),
    ('G', 'T_room', '냉각 도달 온도', 23.0, 'degC', PAPER + ' 3.2.4', '검증완료', '논문과 동일'),
    ('G', 'T_test', '시험 온도 (3 조건)', None, 'degC', PAPER + ' Table 3', '검증완료', '23 / 500 / 1000 degC'),
    ('G', '기계변형률 span', '인장 Step 목표 기계변형률', 0.005334, '-', '자체 설정', '수치설정', '★세 온도에서 반드시 동일해야 비교 가능 (속도 의존성)'),
    ('G', 'PBC', '주기경계조건', None, '-', PAPER + ' 3.2.2 [31]', '검증완료', 'Driver 반력 0, 평균응력 잔차 4.0e-8 (기계정밀도)'),

    ('H. 논문 검증 목표 (Table 3)', None, None, None, None, None, None, None),
    ('H', '23C 실험', '인장강도 실험값', 116.17, 'MPa', PAPER + ' Table 3', '검증완료', '표준편차 +-8.78'),
    ('H', '23C 해석', '인장강도 논문 해석값', 128.45, 'MPa', PAPER + ' Table 3', '검증완료', '★XT=421 보정의 목표값. 실험 대비 오차 10.31%'),
    ('H', '500C 실험', '인장강도 실험값', 160.19, 'MPa', PAPER + ' Table 3', '검증완료', '표준편차 +-14.83'),
    ('H', '500C 해석', '인장강도 논문 해석값', 179.42, 'MPa', PAPER + ' Table 3', '검증완료', '실험 대비 오차 12.00%'),
    ('H', '1000C 실험', '인장강도 실험값', 173.28, 'MPa', PAPER + ' Table 3', '검증완료', '표준편차 +-12.94'),
    ('H', '1000C 해석', '인장강도 논문 해석값', 199.15, 'MPa', PAPER + ' Table 3', '검증완료', '실험 대비 오차 14.93%'),
]

wb = Workbook()

# ---------------- Sheet 1 : 물성전체 ----------------
ws = wb.active
ws.title = '물성전체'
ws['A1'] = 'C/SiC 평직 복합재 UMAT 물성 대장'
ws['A1'].font = Font(F, size=14, bold=True)
ws['A2'] = '재현 대상: ' + PAPER
ws['A2'].font = Font(F, size=10, italic=True)
ws['A3'] = ('상태 구분  |  검증완료: 논문 직접 인용 또는 유도 후 수치 재검증 완료  |  '
            '보정값: 논문에 없어 Table 3 에 맞춰 역보정  |  '
            '임시값: 논문에 없고 미보정  |  '
            '수치설정: 물성이 아닌 수치해석 파라미터  |  '
            '미검증: 논문과 다르며 영향 미확인')
ws['A3'].font = Font(F, size=9)

hdr = ['구분', '물성 이름', '기능', '값', '단위', '출처', '상태', '비고']
r0 = 5
for j, h in enumerate(hdr, 1):
    c = ws.cell(r0, j, h)
    c.font = Font(F, size=10, bold=True, color='FFFFFF')
    c.fill = H_FILL
    c.alignment = Alignment('center', 'center')
    c.border = BOX

r = r0 + 1
for row in ROWS:
    if row[1] is None:
        ws.cell(r, 1, row[0])
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        cc = ws.cell(r, 1)
        cc.font = Font(F, size=11, bold=True, color='1F3864')
        cc.fill = CAT_FILL
        cc.alignment = Alignment('left', 'center')
        for j in range(1, 9):
            ws.cell(r, j).border = BOX
        r += 1
        continue
    cat, name, func, val, unit, src, stat, note = row
    ws.cell(r, 1, cat).alignment = Alignment('center', 'center')
    ws.cell(r, 2, name)
    ws.cell(r, 3, func)
    vc = ws.cell(r, 4, val)
    vc.alignment = Alignment('right', 'center')
    if isinstance(val, float):
        vc.number_format = '0.00E+00' if abs(val) < 1e-3 else '#,##0.000000'
    ws.cell(r, 5, unit).alignment = Alignment('center', 'center')
    ws.cell(r, 6, src)
    sc = ws.cell(r, 7, stat)
    sc.alignment = Alignment('center', 'center')
    sc.fill = STATUS_FILL.get(stat, NUM_FILL)
    sc.font = Font(F, size=10, bold=True)
    ws.cell(r, 8, note)
    for j in range(1, 9):
        cell = ws.cell(r, j)
        cell.border = BOX
        if cell.font.name != F or not cell.font.bold:
            cell.font = Font(F, size=10, bold=(j == 7))
        cell.alignment = Alignment(cell.alignment.horizontal or 'left',
                                   'center', wrap_text=(j in (3, 6, 8)))
    r += 1
last = r - 1

for col, w in zip('ABCDEFGH', (7, 22, 34, 20, 11, 40, 11, 56)):
    ws.column_dimensions[col].width = w
ws.freeze_panes = 'A6'
ws.auto_filter.ref = 'A%d:H%d' % (r0, last)

# ---------------- Sheet 2 : 균질화검증 (live formulas) ----------------
w2 = wb.create_sheet('균질화검증')
w2['A1'] = '얀 물성 균질화 재검증 (Chamis 강성 / Schapery·Chamis 열팽창)'
w2['A1'].font = Font(F, size=13, bold=True)
w2['A2'] = '아래 파란 셀이 입력이다. Vf_tow 를 바꾸면 계산열이 전부 갱신된다.'
w2['A2'].font = Font(F, size=9, italic=True)

INP = [('Ef1', 230000.0, 'MPa', '논문 Table 1'), ('Ef2', 40000.0, 'MPa', '논문 Table 1'),
       ('Gf12', 24000.0, 'MPa', '논문 Table 1'), ('Gf23', 14300.0, 'MPa', '논문 Table 1'),
       ('nu_f12', 0.26, '-', '논문 Table 1'), ('alpha_f1', -0.3e-6, '1/K', '논문 Table 1'),
       ('alpha_f2', 3.1e-6, '1/K', '논문 Table 1'), ('Em', 350000.0, 'MPa', '논문 Table 2'),
       ('nu_m', 0.20, '-', '논문 Table 2'), ('alpha_m', 4.5e-6, '1/K', '논문 Table 2'),
       ('Vf_tow', 0.79194, '-', '역산 (논문 미기재)')]
w2['A4'] = '입력값'
w2['A4'].font = Font(F, size=11, bold=True, color='1F3864')
for j, h in enumerate(['기호', '값', '단위', '출처'], 1):
    c = w2.cell(5, j, h)
    c.font = Font(F, size=10, bold=True, color='FFFFFF')
    c.fill = H_FILL
    c.border = BOX
for i, (k, v, u, s) in enumerate(INP):
    rr = 6 + i
    w2.cell(rr, 1, k).font = Font(F, size=10, bold=True)
    c = w2.cell(rr, 2, v)
    c.font = Font(F, size=10, color='0000FF')
    c.number_format = '0.00E+00' if abs(v) < 1e-3 else '#,##0.00####'
    w2.cell(rr, 3, u).alignment = Alignment('center')
    w2.cell(rr, 4, s)
    for j in range(1, 5):
        w2.cell(rr, j).border = BOX
        if j != 2:
            w2.cell(rr, j).font = Font(F, size=10)
R = {k: 'B%d' % (6 + i) for i, (k, _, _, _) in enumerate(INP)}
GM = '(%s/(2*(1+%s)))' % (R['Em'], R['nu_m'])
SQ = 'SQRT(%s)' % R['Vf_tow']
VM = '(1-%s)' % R['Vf_tow']

CALC = [
    ('Ey1', '={v}*{Ef1}+{Vm}*{Em}'.format(v=R['Vf_tow'], Ef1=R['Ef1'], Vm=VM, Em=R['Em']), 254967.228042),
    ('Ey2', '={Em}/(1-{sq}*(1-{Em}/{Ef2}))'.format(Em=R['Em'], sq=SQ, Ef2=R['Ef2']), 44321.737572),
    ('Gy12', '={gm}/(1-{sq}*(1-{gm}/{Gf12}))'.format(gm=GM, sq=SQ, Gf12=R['Gf12']), 26431.515264),
    ('Gy23', '={gm}/(1-{sq}*(1-{gm}/{Gf23}))'.format(gm=GM, sq=SQ, Gf23=R['Gf23']), 15876.667974),
    ('nu_y12', '={v}*{nf}+{Vm}*{nm}'.format(v=R['Vf_tow'], nf=R['nu_f12'], Vm=VM, nm=R['nu_m']), 0.247516386),
    ('nu_y23', None, 0.395813581),
    ('alpha_y1', None, 1.070925962822e-6),
    ('alpha_y2', None, 3.324908565604e-6),
]
w2['F4'] = '계산 결과 vs UMAT 카드 값'
w2['F4'].font = Font(F, size=11, bold=True, color='1F3864')
for j, h in enumerate(['물성', '식으로 계산', 'UMAT 카드값', '오차 %'], 6):
    c = w2.cell(5, j, h)
    c.font = Font(F, size=10, bold=True, color='FFFFFF')
    c.fill = H_FILL
    c.border = BOX
for i, (k, f, card) in enumerate(CALC):
    rr = 6 + i
    w2.cell(rr, 6, k).font = Font(F, size=10, bold=True)
    if k == 'nu_y23':
        f = '=G7/(2*G9)-1'
    elif k == 'alpha_y1':
        f = ('=({v}*{Ef1}*{af1}+{Vm}*{Em}*{am})/({v}*{Ef1}+{Vm}*{Em})'
             .format(v=R['Vf_tow'], Ef1=R['Ef1'], af1=R['alpha_f1'],
                     Vm=VM, Em=R['Em'], am=R['alpha_m']))
    elif k == 'alpha_y2':
        f = ('={af2}*{sq}+(1-{sq})*(1+{v}*{nm}*{Ef1}/G6)*{am}'
             .format(af2=R['alpha_f2'], sq=SQ, v=R['Vf_tow'],
                     nm=R['nu_m'], Ef1=R['Ef1'], am=R['alpha_m']))
    cg = w2.cell(rr, 7, f)
    cg.number_format = '0.000000E+00' if abs(card) < 1e-3 else '#,##0.000000'
    ch = w2.cell(rr, 8, card)
    ch.number_format = cg.number_format
    ci = w2.cell(rr, 9, '=IFERROR((G%d/H%d-1)*100,"")' % (rr, rr))
    ci.number_format = '0.000000'
    for j in range(6, 10):
        w2.cell(rr, j).border = BOX
        w2.cell(rr, j).font = Font(F, size=10, bold=(j == 6))
w2.cell(15, 6, '판정')
w2.cell(15, 6).font = Font(F, size=10, bold=True)
w2.cell(15, 7, '=IF(SUMPRODUCT(MAX(ABS(I6:I13)))<0.01,"전 항목 오차 0.01% 미만 - 균질화 검증 통과","오차 초과 항목 있음 - 확인 필요")')
w2.cell(15, 7).font = Font(F, size=10, bold=True)
w2.cell(15, 7).fill = OK_FILL
w2.merge_cells('G15:I15')
w2['F17'] = '참고: Chamis 이론 얀 인장강도'
w2['F17'].font = Font(F, size=10, bold=True)
w2['G17'] = '=%s*3580' % R['Vf_tow']
w2['G17'].number_format = '#,##0.0'
w2['H17'] = 'MPa'
w2['I17'] = '=421/G17*100'
w2['I17'].number_format = '0.0"%"'
w2['J17'] = '<- 현재 보정값 421 MPa 이 Chamis 이론값에서 차지하는 비율'
w2['J17'].font = Font(F, size=9, italic=True)
for col, wd in zip('ABCDEFGHI', (12, 16, 8, 26, 3, 12, 18, 18, 12)):
    w2.column_dimensions[col].width = wd

# ---------------- Sheet 3 : 검증요약 ----------------
w3 = wb.create_sheet('검증요약')
w3['A1'] = '검증 상태 요약'
w3['A1'].font = Font(F, size=13, bold=True)
for j, h in enumerate(['상태', '개수', '의미'], 1):
    c = w3.cell(3, j, h)
    c.font = Font(F, size=10, bold=True, color='FFFFFF')
    c.fill = H_FILL
    c.border = BOX
MEAN = {'검증완료': '논문 직접 인용, 또는 유도 후 수치 재검증 완료. 그대로 사용 가능',
        '보정값': '논문에 값이 없어 Table 3 결과에 맞춰 역보정. 재현이 아닌 보정임을 논문에 명시 필요',
        '임시값': '논문에 값이 없고 아직 보정도 안 됨. 결과 민감도 확인 필요',
        '수치설정': '물성이 아닌 수치해석 파라미터. 물리적 의미 없음',
        '미검증': '논문과 다르게 설정했고 영향을 아직 확인 못 함'}
for i, (k, m) in enumerate(MEAN.items()):
    rr = 4 + i
    w3.cell(rr, 1, k).font = Font(F, size=10, bold=True)
    w3.cell(rr, 1).fill = STATUS_FILL[k]
    w3.cell(rr, 2, '=COUNTIF(물성전체!$G$6:$G$%d,A%d)' % (last, rr)).font = Font(F, size=10)
    w3.cell(rr, 2).alignment = Alignment('center')
    w3.cell(rr, 3, m).font = Font(F, size=10)
    w3.cell(rr, 3).alignment = Alignment('left', 'center', wrap_text=True)
    for j in range(1, 4):
        w3.cell(rr, j).border = BOX
rr = 4 + len(MEAN)
w3.cell(rr, 1, '합계').font = Font(F, size=10, bold=True)
w3.cell(rr, 2, '=SUM(B4:B%d)' % (rr - 1)).font = Font(F, size=10, bold=True)
w3.cell(rr, 2).alignment = Alignment('center')
for j in range(1, 4):
    w3.cell(rr, j).border = BOX

w3['A12'] = '우선 처리 대상'
w3['A12'].font = Font(F, size=12, bold=True, color='C00000')
ACT = [
    ('얀 PROPS 18 A1T', '얀 축방향에 크랙밴드(Gf) 정규화가 없어 eta·메쉬 의존성의 근본 원인. '
                        'eta 반감당 최대응력 4% 변동, 수렴점 없음. UMAT 수정 필요'),
    ('얀 PROPS 11 XT', '보정값 421 MPa 은 Chamis 이론값의 14.8%. 논문에 없는 값을 역보정한 것이므로 '
                       '"재현"이 아니라 "보정"임을 반드시 명시'),
    ('얀 PROPS 13 YT', '횡방향 손상률(모델 88~93% vs 논문 99%)을 좌우하는데 미보정'),
    ('기지 PROPS 8/9 DMAX', '손상 상한 때문에 잔류강성이 남아 최대점 이후 응력이 비물리적으로 재상승'),
    ('C. 요소 개수', '174,405개 (논문 116,724개). 메쉬 수렴성 미검증. '
                     '단 얀 정규화가 없으면 수렴점 자체가 존재하지 않음'),
    ('C. RVE 두께', '0.44 mm (논문 0.4334 mm). 1.5% 차이, 영향 미확인'),
]
for j, h in enumerate(['항목', '내용'], 1):
    c = w3.cell(13, j, h)
    c.font = Font(F, size=10, bold=True, color='FFFFFF')
    c.fill = H_FILL
    c.border = BOX
for i, (k, m) in enumerate(ACT):
    rr = 14 + i
    w3.cell(rr, 1, k).font = Font(F, size=10, bold=True)
    w3.cell(rr, 2, m).font = Font(F, size=10)
    w3.cell(rr, 2).alignment = Alignment('left', 'center', wrap_text=True)
    for j in range(1, 3):
        w3.cell(rr, j).border = BOX
    w3.row_dimensions[rr].height = 30
w3.merge_cells('B13:C13')
for i in range(len(ACT)):
    w3.merge_cells(start_row=14 + i, start_column=2, end_row=14 + i, end_column=3)
for col, wd in zip('ABC', (24, 60, 40)):
    w3.column_dimensions[col].width = wd

out = '/tmp/claude-0/-home-user-CDM-UMAT/381478c7-62b9-5b6c-abbe-ab6f0092aab8/scratchpad/CSIC_UMAT_material_properties_0803_1511.xlsx'
wb.save(out)
print('saved', out, 'last data row =', last)
