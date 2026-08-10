# 2. 이론 및 손상 모델

본 장에서는 해석에 사용한 구성 모델을 기술한다. 모델의 골격은 Zhang et al. (2022)이 채택한 Ge et al. (2018)의 연속체 손상역학(CDM) 구성방정식이며, 얀(yarn)과 매트릭스(matrix)를 별개의 재료상으로 취급하는 2상 모델이다. 2.1절에서 구성 성분 물성과 마이크로역학 균질화를, 2.2절에서 얀 손상 모델을, 2.3절에서 매트릭스 탄소성-손상 모델을, 2.4절에서 수치 안정화 기법을 순서대로 정리한다. 이후 장에서는 본 장의 식 번호만을 인용한다.

## 2.1 재료 및 마이크로역학 균질화

대상 재료는 T300 탄소섬유 얀과 SiC 매트릭스로 구성된 2차원 직조 C/SiC 복합재이다. 매트릭스는 등방성으로서 Zhang (2022) Table 2의 물성 $E_m = 350$ GPa, $\nu_m = 0.20$, 강도 $X_{m,t} = X_{m,c} = 310$ MPa, 열팽창계수 $\alpha_m = 4.5\times10^{-6}$ /K를 그대로 사용한다. 무응력(공정) 온도는 PIP 공정 온도인 $T_0 = 1050\,^\circ$C이다.

얀은 횡등방성 균질 재료로 이상화하며, 그 유효 물성은 T300 필라멘트(Zhang Table 1)와 SiC 매트릭스(Table 2) 물성으로부터 Chamis 강성 관계식과 Schapery 열팽창 관계식으로 계산한다. 얀 내 섬유 체적분율을 $V_f$라 할 때 탄성 상수는 다음과 같다.

$$E_1 = V_f E_{f1} + (1-V_f)E_m \tag{2.1}$$

$$E_2 = E_3 = \frac{E_m}{1-\sqrt{V_f}\left(1-E_m/E_{f2}\right)} \tag{2.2}$$

$$G_{12} = G_{13} = \frac{G_m}{1-\sqrt{V_f}\left(1-G_m/G_{f12}\right)}, \qquad G_{23} = \frac{G_m}{1-\sqrt{V_f}\left(1-G_m/G_{f23}\right)} \tag{2.3}$$

$$\nu_{12} = \nu_{13} = V_f\,\nu_{f12} + (1-V_f)\,\nu_m, \qquad \nu_{23} = \frac{E_2}{2G_{23}} - 1 \tag{2.4}$$

여기서 아래첨자 $f$는 섬유, $m$은 매트릭스 물성을 나타내고, 방향 1은 섬유 종방향이다. 열팽창계수는 Schapery 관계식으로 구한다.

$$\alpha_1 = \frac{V_f E_{f1}\alpha_{f1} + (1-V_f)E_m\alpha_m}{V_f E_{f1} + (1-V_f)E_m} \tag{2.5}$$

$$\alpha_2 = \alpha_3 = \sqrt{V_f}\,\alpha_{f2} + \left(1-\sqrt{V_f}\right)\left[(1+\nu_m)\alpha_m - \nu_m\,\alpha_1\right] \tag{2.6}$$

식 (2.1)–(2.6)에 $V_f = 0.792$를 대입하면 $E_1 = 254{,}967$ MPa, $E_2 = E_3 = 44{,}322$ MPa, $\nu_{12} = 0.2475$, $\nu_{23} = 0.3958$, $G_{12} = G_{13} = 26{,}431$ MPa, $G_{23} = 15{,}877$ MPa, $\alpha_1 = 1.071\times10^{-6}$ /K, $\alpha_2 = \alpha_3 = 3.325\times10^{-6}$ /K가 얻어지며, 이는 해석에 투입한 얀 상수를 최대 상대오차 0.142 % 이내로 재현하는 검증된 값이다. 이때 복합재 전체의 섬유 체적분율은 약 39.6 %로 원 논문이 보고한 "약 40 %"와 일치한다. 얀·매트릭스의 탄성 및 열 물성은 온도에 무관한 상수로 두며, 온도별 거동 차이는 전적으로 열잔류응력의 재분포에서 발생하도록 한다(Zhang 2022 §3.2.3).

## 2.2 얀 손상 모델

### 2.2.1 유효응력과 손상 강성

얀의 명목응력 $\boldsymbol{\sigma}$는 손상된 강성 $\mathbf{C}(d)$와 탄성 변형률의 곱으로, 손상 개시 판정에 쓰이는 유효응력 $\tilde{\boldsymbol{\sigma}}$는 비손상 강성 $\mathbf{C}_0$로 계산한다(Ge (2018) 식 (2)–(4)).

$$\boldsymbol{\sigma} = \mathbf{C}(d):\boldsymbol{\varepsilon}^e, \qquad \tilde{\boldsymbol{\sigma}} = \mathbf{C}_0:\boldsymbol{\varepsilon}^e \tag{2.7}$$

손상 강성 $\mathbf{C}(d)$는 컴플라이언스 기반 저감으로 구성하며, 수직 성분에는 종방향 손상변수 $d_1$과 횡방향 손상변수 $d_2 = d_3 = d_t$를, 전단 성분에는 다음의 결합 손상을 적용한다(Ge (2018) 식 (3)).

$$d_4 = 1-(1-d_1)(1-d_2), \quad d_5 = 1-(1-d_2)(1-d_3), \quad d_6 = 1-(1-d_1)(1-d_3) \tag{2.8}$$

인장·압축 모드별 손상변수 $d_I$ ($I = 1t, 1c, 2t, 2c$)는 각 방향에서 $d_1 = 1-(1-d_{1t})(1-d_{1c})$, $d_t = 1-(1-d_{2t})(1-d_{2c})$로 결합된다.

### 2.2.2 3차원 Hashin 손상 개시

손상 개시는 유효응력에 대한 3차원 Hashin 판정식(Zhang (2022) 식 (11)–(14), $\alpha=\beta=1$)으로 평가한다. 섬유 종방향 인장($\tilde\sigma_{11}\ge 0$)과 압축은

$$\phi_{1t} = \sqrt{\left(\frac{\tilde\sigma_{11}}{X_t}\right)^2 + \left(\frac{\tilde\sigma_{12}}{S_{12}}\right)^2 + \left(\frac{\tilde\sigma_{13}}{S_{13}}\right)^2}, \qquad \phi_{1c} = \frac{|\tilde\sigma_{11}|}{X_c} \tag{2.9}$$

이고, 횡방향 인장($\tilde\sigma_{22}+\tilde\sigma_{33}\ge 0$)과 압축은 각각 다음과 같다.

$$\phi_{2t} = \sqrt{\left(\frac{\tilde\sigma_{22}+\tilde\sigma_{33}}{Y_t}\right)^2 + \frac{\tilde\sigma_{23}^2 - \tilde\sigma_{22}\tilde\sigma_{33}}{S_{23}^2} + \left(\frac{\tilde\sigma_{12}}{S_{12}}\right)^2 + \left(\frac{\tilde\sigma_{13}}{S_{13}}\right)^2} \tag{2.10}$$

$$\phi_{2c} = \sqrt{\left[\left(\frac{Y_c}{2S_{23}}\right)^2 - 1\right]\frac{\tilde\sigma_{22}+\tilde\sigma_{33}}{Y_c} + \left(\frac{\tilde\sigma_{22}+\tilde\sigma_{33}}{2S_{23}}\right)^2 + \frac{\tilde\sigma_{23}^2 - \tilde\sigma_{22}\tilde\sigma_{33}}{S_{23}^2} + \left(\frac{\tilde\sigma_{12}}{S_{12}}\right)^2 + \left(\frac{\tilde\sigma_{13}}{S_{13}}\right)^2} \tag{2.11}$$

각 모드의 손상 개시 지표 $r_I$는 하중 이력상 최댓값으로 정의하여 비가역성을 보장한다.

$$r_I(t) = \max\left(1,\ \max_{\tau\le t}\phi_I(\tau)\right) \tag{2.12}$$

강도 파라미터 중 종방향 강도는 섬유 지배 혼합법칙으로 유도한 $X_t = V_f\cdot 3580 = 2835$ MPa, $X_c = V_f\cdot 2470 = 1956$ MPa를 시작값으로 사용한다. 반면 횡방향·전단 강도 $Y_t, Y_c, S_{12}, S_{13}, S_{23}$는 원 논문이 값을 공개하지 않았으므로 논문 미공개 → 보정 대상 파라미터이며, 그 보정 절차는 4장에서 다룬다.

### 2.2.3 지수형 손상발전과 균열대 정규화

$r_I > 1$이 되면 손상변수는 지수형 발전식(Zhang (2022) 식 (17))을 따른다.

$$d_I = 1 - \frac{1}{r_I}\exp\left[A_I(1-r_I)\right] \tag{2.13}$$

계수 $A_I$는 연화 기울기, 즉 파괴 시 소산되는 에너지를 결정한다. 국부 연화 모델은 요소 크기에 따라 소산 에너지가 달라지는 병리적 격자 의존성을 가지므로, 균열대 정규화(crack-band regularization)로 $A_I$를 요소별로 재산정한다(Ge (2018) 식 (19)–(21)). 지수형 법칙에 대한 폐형식은

$$A_I = \frac{2\, g_{0,I}\, l_c}{G_{f,I} - g_{0,I}\, l_c}, \qquad g_{0,I} = \frac{X_I^2}{2E_I} \tag{2.14}$$

이다. 여기서 $G_{f,I}$는 모드별 파괴에너지(N/mm), $l_c$는 Abaqus가 제공하는 특성요소길이(CELENT), $g_{0,I}$는 개시 시점까지의 탄성 변형에너지 밀도, $X_I$와 $E_I$는 해당 모드의 강도와 탄성계수이다. $G_{f,I} \le g_{0,I}l_c$이면 스냅백이 발생하므로 $A_I$는 상한 50으로 제한하며, $G_{f,I} = 0$으로 두면 고정 계수 $A_I$(시작값 2.0)를 사용한다. 종방향 파괴에너지는 Ge (2018) Table 3의 $G_{f,1t} = G_{f,1c} = 12.5$ N/mm를 시작값으로 채택한다.

### 2.2.4 종방향 인장의 혼합 선형-지수 법칙

직조 C/SiC의 종방향(warp 얀) 인장 파괴는 섬유 풀아웃을 동반하는 점진적 파괴로서, 순수 지수 연화보다 완만한 꼬리(tail)를 가진다. 이를 반영하여 $I = 1t$ 모드에 한해 Zhang (2022) 식 (18)의 혼합 선형-지수 법칙을 적용한다. Ge (2018) 식 (16)–(17)의 보조변수를 사용하면

$$d_L = \left(1+\frac{K_1}{E_1}\right)\left(1-\frac{1}{r_L}\right), \qquad r_L = \min(r_{1t},\, r_F) \tag{2.15}$$

$$d_{1t} = 1 - \frac{1-d_L}{r_E}\exp\left[A_{1t}(1-r_E)\right], \qquad r_E = \max\left(1,\ (1-d_F)\,\frac{X_t}{X_{PO}}\, r_{1t}\right) \tag{2.16}$$

이다. 여기서 $d_F$는 $r_L = r_F$에서 식 (2.15)로 평가한 전이 시점 손상값이다. 즉 $r_{1t} \le r_F$ 구간에서는 기울기 $-K_1$의 선형 연화가, $r_{1t} > r_F$에서는 풀아웃 응력 수준 $X_{PO}$로 스케일된 지수 연화가 작동한다. 파라미터 $X_{PO}$(풀아웃 응력), $r_F$(선형→지수 전이 지표), $K_1$(선형 연화 기울기)은 원 논문이 값을 공개하지 않은 논문 미공개 → 보정 대상 파라미터로서, 물리적 근거에 따라 $X_{PO} \approx 0.2\text{–}0.3\,X_t$, $r_F \approx 2\text{–}4$, $K_1$은 $E_1$의 수 % 수준에서 보정을 시작한다. $X_{PO} \le 0$으로 두면 식 (2.13)의 순수 지수 법칙으로 환원되는 스위치 구조이다.

## 2.3 매트릭스 모델

### 2.3.1 변형률 분해와 탄소성

SiC 매트릭스는 결합된 탄소성-손상 모델로 기술한다. 전체 변형률은 탄성·소성·열 성분으로 분해된다(Ge (2018) 식 (6)).

$$\boldsymbol{\varepsilon} = \boldsymbol{\varepsilon}^e + \boldsymbol{\varepsilon}^p + \boldsymbol{\varepsilon}^{th} \tag{2.17}$$

열 변형률 $\boldsymbol{\varepsilon}^{th}$는 Abaqus의 `*Expansion`(무응력 온도 1050 °C)으로 부과되어 UMAT에는 역학적 변형률만 전달되므로, 구성 계산에서는 유효응력을

$$\tilde{\boldsymbol{\sigma}} = \mathbf{C}_0 : \left(\boldsymbol{\varepsilon} - \boldsymbol{\varepsilon}^p\right) \tag{2.18}$$

로 평가한다. 소성은 유효응력 공간에서의 von Mises 연합 유동(associated flow)과 선형 등방 경화로 모델링하며(Ge (2018) 식 (8)–(9)), 항복함수는

$$f = \sigma_{vM}(\tilde{\boldsymbol{\sigma}}) - \left(\sigma_{Y0} + H_{iso}\,\bar{p}\right) \le 0 \tag{2.19}$$

이다. 여기서 $\bar{p}$는 등가 소성 변형률이고, 반환 사상(radial return)으로 $\Delta\bar{p} = (\sigma_{vM}^{tr} - \sigma_Y)/(3G_m + H_{iso})$를 폐형식으로 구한다. 이 소성 항이 원 논문이 보고한 매트릭스의 유사연성(pseudo-ductility)과 하중 제거 후 잔류변형을 재현한다. 초기 항복응력 $\sigma_{Y0}$(SY0)와 등방 경화계수 $H_{iso}$(HISO)는 원 논문에 값이 없는 논문 미공개 → 보정 대상 파라미터이며, C/SiC의 작은 잔류변형을 고려하여 $\sigma_{Y0} \approx 250$ MPa, $H_{iso} \approx 10^5$ MPa에서 보정을 시작한다. $\sigma_{Y0} \le 0$이면 소성이 비활성화된다.

### 2.3.2 손상 개시와 발전

매트릭스 손상 개시는 유효응력의 von Mises 등가응력 $\sigma_{vM}$을 유효응력 제1불변량 $I_1 = \tilde\sigma_{11}+\tilde\sigma_{22}+\tilde\sigma_{33}$의 부호에 따라 인장 또는 압축 강도로 나누어 판정한다(Zhang (2022) 식 (15)–(16)).

$$\phi_{m} = \begin{cases} \sigma_{vM}(\tilde{\boldsymbol{\sigma}})/X_{m,t}, & I_1 \ge 0 \\[4pt] \sigma_{vM}(\tilde{\boldsymbol{\sigma}})/X_{m,c}, & I_1 < 0 \end{cases} \tag{2.20}$$

손상발전은 얀과 동일한 지수형 법칙 식 (2.13)(Zhang (2022) 식 (19))을 따르고, 계수 $A_{m}$ 역시 식 (2.14)의 균열대 정규화로 파괴에너지 $G_{f,m}$과 $l_c$로부터 요소별로 산정한다. 취성 SiC를 반영하여 $G_{f,m} = 0.031$ N/mm를 시작값으로 둔다. 강성 저감은 $I_1$의 부호에 따라 인장 손상 또는 압축 손상이 활성화되는 등방 컴플라이언스 저감이다(Ge (2018) 식 (7)). 강도 $X_{m,t} = X_{m,c} = 310$ MPa는 검증된 논문 공개값으로 고정한다.

냉각 단계(1050 °C → 시험온도)에서 매트릭스는 얀과의 열팽창계수 불일치로 잔류 인장을 받아 광범위하게 손상되며(원 논문: 845 °C에서 손상률 100 %), 이후 인장 단계의 극한강도는 주로 얀 손상이 지배한다. 시험온도가 높을수록 냉각 구간이 짧아져 열잔류응력이 완화되고, 이것이 온도 상승에 따른 강도 증가 추세의 원천이 된다.

## 2.4 점성 정규화와 수치 안정화

연화 구간에서 접선 강성이 음이 되면 정적 음해법의 수렴이 어려워지므로, 손상변수 갱신에 점성 정규화를 적용한다. 시간 증분 $\Delta t$에서 식 (2.13)·(2.15)–(2.16)·(2.20)이 주는 목표 손상값 $d_I^{tar}$에 대해

$$d_I^{\,n+1} = d_I^{\,n} + \frac{\Delta t}{\eta + \Delta t}\left(d_I^{tar} - d_I^{\,n}\right) \tag{2.21}$$

로 지연 갱신한다. 점성 계수는 $\eta = 0.02$를 기본으로 하되, Ge (2018) §3.2의 권고대로 해의 속도의존성이 무시될 만큼 작게 유지한다. 아울러 손상변수의 상한을 $d_{max} = 0.99$로 두어 완전파괴($d=1$)에 따른 강성 특이점을 방지하고, 한 증분 내 손상 점프가 과대하면 시간 증분을 자동 축소(cutback)하는 제어를 병용한다. 야코비안은 손상된 할선 강성으로 구성한다. 이들 수치 장치는 해의 물리적 내용을 바꾸지 않는 안정화 수단이며, 구체적 해석 절차와 증분 설정은 3장에서 기술한다.
