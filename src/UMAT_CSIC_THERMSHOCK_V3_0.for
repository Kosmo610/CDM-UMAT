C=======================================================================
C  UMAT_CSIC_THERMSHOCK_V3_0.for
C
C  Thesis-line UMAT for the 2-scale cyclic-thermal-shock study of
C  2D plain-weave C/SiC.  V3_0 is a strict superset of the verified
C  V1_0 replication UMAT (UMAT_CSIC_RVE_ZHANG2022_V1_0.for):
C
C    * every V1_0 card runs unchanged and gives bit-identical results
C      (the new blocks are appended to the card and are inactive when
C       absent -- see the NPROPS rules below),
C    * three new capabilities are added on top.
C
C  NEW IN V3_0
C  -----------
C  (1) TEMPERATURE-DEPENDENT PROPERTIES.  Piecewise-linear multiplier
C      tables f(T) appended to the card, evaluated at T = TEMP+DTEMP by
C      KPROP_INTERP.  Clamped outside the table (never extrapolated).
C      Multipliers -- not absolute values -- so the verified V1_0 base
C      constants stay visible in the card and f=1 recovers them exactly.
C
C      NOTE ON CTE:  alpha(T) is NOT handled here.  Abaqus *EXPANSION
C      already supports a temperature-dependent secant CTE referenced
C      to the stress-free temperature,
C         eps_th = alpha(T)(T-T0) - alpha(Ti)(Ti-T0),
C      which is exactly the integral the thermal residual stress needs.
C      Put alpha(T) rows under *EXPANSION, zero=1050.  The UMAT keeps
C      receiving MECHANICAL strain.
C
C  (2) UNILATERAL DAMAGE (CRACK CLOSURE).  Thermal cycling reverses the
C      sign of the normal strains every cycle, so damage opened in
C      tension must partially deactivate when the crack closes, else the
C      stiffness loss is overpredicted.  Controlled by HCLO in [0,1]:
C         d_eff = d            if eps_normal >= 0   (crack open)
C         d_eff = d*(1-HCLO)   if eps_normal <  0   (crack closed)
C      HCLO=0 reproduces V1_0; HCLO=1 is full stiffness recovery.
C      Shear damage is NOT recovered (closed crack faces still slide
C      with degraded shear stiffness) -- the usual assumption.
C      The stored history d is untouched: closure changes the secant
C      stiffness only, damage stays monotonic.
C
C  (3) MACRO HOMOGENISED CDM WITH CYCLE-DEPENDENT DAMAGE (KMACRO31).
C      A history-variable CDM shakes down after the first cycle: under a
C      repeated identical thermal load the failure index never exceeds
C      the stored threshold r, so dr=0 and N=1 looks like N=100.  The
C      macro law therefore carries a second, cycle-driven damage:
C
C         Delta d_cyc = C(T) * <r_drv - RTH>^n * (1-d_cyc)^(-k) * dN
C         dN          = (cycle rate) * DTIME
C         1 - d_tot   = (1 - d_mono) * (1 - w * d_cyc)
C
C      r_drv is the dimensionless maximum failure index (=1 at static
C      initiation), so RTH is an endurance limit as a fraction of static
C      strength and n plays the role of the Basquin exponent -- both
C      calibratable against published residual-strength-vs-N data.
C      w = 1 transverse / W1CYC longitudinal (fibre direction degrades
C      less than the matrix-dominated directions).
C      The cycle rate lets one increment represent many cycles, i.e.
C      the CYCLE-JUMP scheme: supply it as field variable PREDEFN
C      (*FIELD) to jump DeltaN cycles per step, or as the constant
C      CYCRATE for explicitly resolved cycles.
C
C  MATERIAL ROUTING (by CMNAME, checked in this order)
C  ---------------------------------------------------
C    'MACRO'  -> KMACRO31  homogenised orthotropic CDM  (macro scale)
C    'YARN'   -> KYARN31   Ge/Zhang yarn CDM            (RVE)
C    'MATRIX' -> KMTRX31   Ge/Zhang matrix CDM          (RVE)
C
C  CARD LAYOUTS
C  ------------
C  YARN   NPROPS = 38                      -> V1_0 card, NT=0, HCLO=0
C         NPROPS = 40 + 7*NT               -> V3_0 card
C     1..38  exactly the V1_0 yarn card (see V1_0 header)
C     39     HCLO   crack-closure recovery fraction (0..1)
C     40     NT     number of temperature points (0 = off)
C     41..   NT rows of 7:  T, fE1, fE2, fG, fX, fY, fS
C            fE1 -> E1, fE2 -> E2,E3, fG -> G12,G13,G23
C            fX  -> Xt,Xc (and X_PO; K1 scales with fE1)
C            fY  -> Yt,Yc      fS -> S12,S13,S23
C
C  MATRIX NPROPS = 22                      -> V1_0 card, NT=0
C         NPROPS = 23 + 4*NT               -> V3_0 card
C     1..22  exactly the V1_0 matrix card (PROPS(22)=30.0 key)
C     23     NT
C     24..   NT rows of 4:  T, fE, fX, fSY
C            fE -> E (and HISO), fX -> Xt,Xc, fSY -> SY0
C     (no HCLO: the matrix already switches tensile/compressive damage
C      on sign(I1) per Ge Eq.7, which is its unilateral effect.)
C
C  MACRO  NPROPS = 47 + 8*NT
C     1      phase id (3.0)
C     2-10   E1 E2 E3 nu12 nu13 nu23 G12 G13 G23   (homogenised)
C     11-17  Xt Xc Yt Yc S12 S13 S23               (homogenised)
C     18-21  A1t A1c Att Atc      22-23 dmax1 dmaxt
C     24     eta       25 max_djump   26 freeze_step   27 min_PNEWDT
C     28     enable    29-31 cut trig/safety/maxf
C     32-35  G1t G1c Gtt Gtc (N/mm; 0 = use fixed A)
C     36     CARD KEY = 31.0 (guard)
C     37     HCLO    crack-closure recovery fraction (0..1)
C     38     CYCON   cycle-damage master switch (0 = off)
C     39     CCYC    C      40 NEXP  n      41 KEXP  k
C     42     RTH     endurance threshold on the failure index
C     43     DCYMAX  cap on d_cyc      44 W1CYC  longitudinal weight
C     45     CYCRATE constant cycle rate (cycles per unit time)
C     46     PREDEFN index of the field variable carrying the cycle
C                    rate (0 = use CYCRATE)
C     47     NT
C     48..   NT rows of 8:  T, fE1, fE2, fG, fX, fY, fS, fC
C            fC -> CCYC (oxidation/interface-wear acceleration with T)
C
C  STATE VARIABLES
C  ---------------
C  YARN   NSTATV >= 16, as V1_0.  17 (optional) = closure flag.
C  MATRIX NSTATV >= 20, identical to V1_0.
C  MACRO  NSTATV >= 22:
C     1 D1T  2 D1C  3 DTT  4 DTC     (monotonic, per mode)
C     5 R1T  6 R1C  7 RTT  8 RTC     (damage thresholds)
C     9 D1   10 DT                   (TOTAL, incl. cycle damage)
C     11 MODE 12 TINIT 13 DJUMP 14 CUTREQ 15 TJUMP 16 RJUMP
C     17 DCYC   cycle damage
C     18 NCUM   accumulated cycles seen by this point
C     19 RDRV   current driving failure index
C     20 D1MONO 21 DTMONO            (monotonic only, for post-proc)
C     22 CLOFLG number of closed directions this increment (0..3)
C
C  Provenance of the base model: Ge et al., Compos. Sci. Technol. 157
C  (2018) 86-98, as used by Zhang et al., Ceram. Int. 48 (2022)
C  3109-3124.  Items (1)-(3) above are additions of this work and are
C  NOT in either paper.
C=======================================================================
      SUBROUTINE UMAT(STRESS,STATEV,DDSDDE,SSE,SPD,SCD,
     1 RPL,DDSDDT,DRPLDE,DRPLDT,STRAN,DSTRAN,TIME,DTIME,TEMP,
     2 DTEMP,PREDEF,DPRED,CMNAME,NDI,NSHR,NTENS,NSTATV,PROPS,
     3 NPROPS,COORDS,DROT,PNEWDT,CELENT,DFGRD0,DFGRD1,
     4 NOEL,NPT,LAYER,KSPT,KSTEP,KINC)
      INCLUDE 'ABA_PARAM.INC'
      CHARACTER*80 CMNAME
      DIMENSION STRESS(NTENS),STATEV(NSTATV),
     1 DDSDDE(NTENS,NTENS),DDSDDT(NTENS),DRPLDE(NTENS),
     2 STRAN(NTENS),DSTRAN(NTENS),TIME(2),PREDEF(1),DPRED(1),
     3 PROPS(NPROPS),COORDS(3),DROT(3,3),DFGRD0(3,3),
     4 DFGRD1(3,3)
      DOUBLE PRECISION EPS(6),SOLD(6),SSEOLD,SPDOLD,WORK,DW,FLDV
      INTEGER I,J,NT,IPF
C
      IF (NTENS.NE.6 .OR. NDI.NE.3 .OR. NSHR.NE.3) THEN
         WRITE(7,*) 'THERMSHOCK V3_0 UMAT: 3-D solid elements only.'
         CALL XIT
      END IF
      DO I=1,6
         EPS(I)=STRAN(I)+DSTRAN(I)
         SOLD(I)=STRESS(I)
         DDSDDT(I)=0.0D0
         DRPLDE(I)=0.0D0
         DO J=1,6
            DDSDDE(I,J)=0.0D0
         END DO
      END DO
      SSEOLD=SSE
      SPDOLD=SPD
      SCD=0.0D0
      RPL=0.0D0
      DRPLDT=0.0D0
      IF (PNEWDT.LE.0.0D0) PNEWDT=1.0D0
C
      IF (INDEX(CMNAME,'MACRO').GT.0) THEN
         IF (NPROPS.LT.47 .OR. NSTATV.LT.22 .OR.
     1       ABS(PROPS(36)-31.0D0).GT.1.0D-6) THEN
            WRITE(7,*) 'V3_0 MACRO card needs NPROPS>=47 with'
            WRITE(7,*) 'PROPS(36)=31.0 as key and NSTATV>=22.'
            WRITE(7,*) 'Got NPROPS,NSTATV=',NPROPS,NSTATV
            CALL XIT
         END IF
         NT=NINT(PROPS(47))
         IF (NT.LT.0 .OR. NPROPS.NE.47+8*NT) THEN
            WRITE(7,*) 'V3_0 MACRO: NPROPS must equal 47+8*NT.'
            WRITE(7,*) 'NT,NPROPS=',NT,NPROPS
            CALL XIT
         END IF
C        Cycle rate from a *FIELD variable when PREDEFN>0.
         FLDV=0.0D0
         IPF=NINT(PROPS(46))
         IF (IPF.GT.0) FLDV=PREDEF(1)+DPRED(1)
         CALL KMACRO31(EPS,STRESS,DDSDDE,STATEV,PROPS,NT,
     1        DTIME,TEMP,DTEMP,FLDV,PNEWDT,KSTEP,CELENT)
      ELSE IF (INDEX(CMNAME,'YARN').GT.0) THEN
         IF (NSTATV.LT.16) THEN
            WRITE(7,*) 'V3_0 YARN card needs NSTATV>=16. Got',NSTATV
            CALL XIT
         END IF
         IF (NPROPS.EQ.38) THEN
            NT=0
         ELSE IF (NPROPS.GE.40) THEN
            NT=NINT(PROPS(40))
            IF (NT.LT.0 .OR. NPROPS.NE.40+7*NT) THEN
               WRITE(7,*) 'V3_0 YARN: NPROPS must be 38 or 40+7*NT.'
               WRITE(7,*) 'NT,NPROPS=',NT,NPROPS
               CALL XIT
            END IF
         ELSE
            WRITE(7,*) 'V3_0 YARN: NPROPS must be 38 or 40+7*NT. Got',
     1                 NPROPS
            CALL XIT
         END IF
         CALL KYARN31(EPS,STRESS,DDSDDE,STATEV,PROPS,NPROPS,NT,
     1        DTIME,TEMP,DTEMP,PNEWDT,KSTEP,CELENT,NSTATV)
      ELSE IF (INDEX(CMNAME,'MATRIX').GT.0) THEN
         IF (NSTATV.LT.20 .OR. ABS(PROPS(22)-30.0D0).GT.1.0D-6) THEN
            WRITE(7,*) 'V3_0 MATRIX card needs PROPS(22)=30.0 and'
            WRITE(7,*) 'NSTATV>=20. Got NPROPS,NSTATV=',NPROPS,NSTATV
            CALL XIT
         END IF
         IF (NPROPS.EQ.22) THEN
            NT=0
         ELSE IF (NPROPS.GE.23) THEN
            NT=NINT(PROPS(23))
            IF (NT.LT.0 .OR. NPROPS.NE.23+4*NT) THEN
               WRITE(7,*) 'V3_0 MATRIX: NPROPS must be 22 or 23+4*NT.'
               WRITE(7,*) 'NT,NPROPS=',NT,NPROPS
               CALL XIT
            END IF
         ELSE
            WRITE(7,*) 'V3_0 MATRIX: bad NPROPS=',NPROPS
            CALL XIT
         END IF
         CALL KMTRX31(EPS,STRESS,DDSDDE,STATEV,PROPS,NT,
     1        DTIME,TEMP,DTEMP,PNEWDT,KSTEP,CELENT)
      ELSE
         WRITE(7,*) 'Unknown CMNAME in V3_0 UMAT: ',CMNAME
         CALL XIT
      END IF
C
      WORK=0.0D0
      SSE=0.0D0
      DO I=1,6
         WORK=WORK+0.5D0*(SOLD(I)+STRESS(I))*DSTRAN(I)
         SSE=SSE+0.5D0*STRESS(I)*EPS(I)
      END DO
      DW=WORK-(SSE-SSEOLD)
      SPD=MAX(SPDOLD,SPDOLD+MAX(0.0D0,DW))
      RETURN
      END
C=======================================================================
      SUBROUTINE KYARN31(EPS,STRESS,CTAN,SV,P,NPROPS,NT,DTIME,
     1 TEMP,DTEMP,PNEWDT,KSTEP,CELENT,NSTATV)
C     V1_0 KYARN30 + temperature-dependent multipliers + unilateral
C     crack closure.  NT=0 and HCLO=0 reproduce KYARN30 exactly.
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      DOUBLE PRECISION C0(6,6),CD(6,6),SE(6),F(6)
      DOUBLE PRECISION E1,E2,E3,NU12,NU13,NU23,G12,G13,G23
      DOUBLE PRECISION XT,XC,YT,YC,S12,S13,S23
      DOUBLE PRECISION A1T,A1C,ATT,ATC,DMAX1,DMAXT,ETA,DJMAX
      DOUBLE PRECISION PMIN,ENABLE,FREEZE,CUTTRG,CUTSAF,CUTMXF
      DOUBLE PRECISION G1T,G1C,GTT,GTC,XPO,RFT,XK1,HCLO
      DOUBLE PRECISION FI1T,FI1C,FITT,FITC,SUMT,TERM
      DOUBLE PRECISION R1T,R1C,RTT,RTC,TAR,GAM,TQ
      DOUBLE PRECISION D1T0,D1C0,DTT0,DTC0,D1T,D1C,DTT,DTC
      DOUBLE PRECISION D1,DT,D1E,DT2E,DT3E
      DOUBLE PRECISION DS12,DS23,DS31,DJ,TEND,RFAC,REQ,CREQ
      DOUBLE PRECISION B1T,B1C,BTT,BTC
      INTEGER I,J,KSTEP,MODE,NT,NPROPS,NSTATV,NCLO
C
      E1=P(2)
      E2=P(3)
      E3=P(4)
      NU12=P(5)
      NU13=P(6)
      NU23=P(7)
      G12=P(8)
      G13=P(9)
      G23=P(10)
      XT=P(11)
      XC=P(12)
      YT=P(13)
      YC=P(14)
      S12=P(15)
      S13=P(16)
      S23=P(17)
      A1T=P(18)
      A1C=P(19)
      ATT=P(20)
      ATC=P(21)
      DMAX1=P(22)
      DMAXT=P(23)
      ETA=P(24)
      DJMAX=P(25)
      FREEZE=P(26)
      PMIN=P(27)
      ENABLE=P(28)
      CUTTRG=MAX(1.0D0,P(29))
      CUTSAF=P(30)
      CUTMXF=P(31)
      G1T=P(32)
      G1C=P(33)
      GTT=P(34)
      GTC=P(35)
      XPO=P(36)
      RFT=P(37)
      XK1=P(38)
      HCLO=0.0D0
      IF (NPROPS.GE.40) HCLO=MIN(1.0D0,MAX(0.0D0,P(39)))
C
C     Temperature-dependent multipliers f(T) at the end of increment.
      TEND=TEMP+DTEMP
      TQ=TEND
      CALL KPROP_INTERP(TQ,P,41,NT,6,F)
      E1=E1*F(1)
      E2=E2*F(2)
      E3=E3*F(2)
      G12=G12*F(3)
      G13=G13*F(3)
      G23=G23*F(3)
      XT=XT*F(4)
      XC=XC*F(4)
      XPO=XPO*F(4)
      XK1=XK1*F(1)
      YT=YT*F(5)
      YC=YC*F(5)
      S12=S12*F(6)
      S13=S13*F(6)
      S23=S23*F(6)
C
      CALL KORTHO(E1,E2,E3,NU12,NU13,NU23,G12,G13,G23,C0)
      CALL KMATVEC6(C0,EPS,SE)
C
C     Effective-stress 3-D Hashin criteria (Zhang Eqs.11-14).
      FI1T=0.0D0
      FI1C=0.0D0
      FITT=0.0D0
      FITC=0.0D0
      IF (SE(1).GE.0.0D0) THEN
         FI1T=SQRT((SE(1)/XT)**2+(SE(4)/S12)**2+
     1              (SE(5)/S13)**2)
      ELSE
         FI1C=ABS(SE(1))/XC
      END IF
      SUMT=SE(2)+SE(3)
      IF (SUMT.GE.0.0D0) THEN
         TERM=(SUMT/YT)**2+(SE(6)*SE(6)-SE(2)*SE(3))/
     1        (S23*S23)+(SE(4)/S12)**2+(SE(5)/S13)**2
         FITT=SQRT(MAX(0.0D0,TERM))
      ELSE
         TERM=((YC/(2.0D0*S23))**2-1.0D0)*SUMT/YC+
     1        (SUMT/(2.0D0*S23))**2+
     2        (SE(6)*SE(6)-SE(2)*SE(3))/(S23*S23)+
     3        (SE(4)/S12)**2+(SE(5)/S13)**2
         FITC=SQRT(MAX(0.0D0,TERM))
      END IF
C
      D1T0=MAX(0.0D0,MIN(DMAX1,SV(1)))
      D1C0=MAX(0.0D0,MIN(DMAX1,SV(2)))
      DTT0=MAX(0.0D0,MIN(DMAXT,SV(3)))
      DTC0=MAX(0.0D0,MIN(DMAXT,SV(4)))
      R1T=MAX(SV(5),FI1T)
      R1C=MAX(SV(6),FI1C)
      RTT=MAX(SV(7),FITT)
      RTC=MAX(SV(8),FITC)
      D1T=D1T0
      D1C=D1C0
      DTT=DTT0
      DTC=DTC0
C
      CALL KABAND(XT*XT/(2.0D0*E1)*CELENT,G1T,A1T,B1T)
      CALL KABAND(XC*XC/(2.0D0*E1)*CELENT,G1C,A1C,B1C)
      CALL KABAND(YT*YT/(2.0D0*E2)*CELENT,GTT,ATT,BTT)
      CALL KABAND(YC*YC/(2.0D0*E2)*CELENT,GTC,ATC,BTC)
C
      IF (ENABLE.GT.0.5D0 .AND. DBLE(KSTEP).LE.FREEZE) THEN
         IF (ETA.GT.0.0D0) THEN
            GAM=DTIME/(ETA+DTIME)
         ELSE
            GAM=1.0D0
         END IF
         IF (XPO.GT.0.0D0) THEN
            CALL KMIX1T(R1T,B1T,E1,XT,XPO,RFT,XK1,TAR)
         ELSE
            CALL KDAMAGE_TARGET(R1T,B1T,1.0D0,TAR)
         END IF
         TAR=MIN(DMAX1,TAR)
         D1T=MAX(D1T0,D1T0+GAM*(TAR-D1T0))
         CALL KDAMAGE_TARGET(R1C,B1C,DMAX1,TAR)
         D1C=MAX(D1C0,D1C0+GAM*(TAR-D1C0))
         CALL KDAMAGE_TARGET(RTT,BTT,DMAXT,TAR)
         DTT=MAX(DTT0,DTT0+GAM*(TAR-DTT0))
         CALL KDAMAGE_TARGET(RTC,BTC,DMAXT,TAR)
         DTC=MAX(DTC0,DTC0+GAM*(TAR-DTC0))
      END IF
C
      D1=1.0D0-(1.0D0-D1T)*(1.0D0-D1C)
      DT=1.0D0-(1.0D0-DTT)*(1.0D0-DTC)
      D1=MIN(0.999D0,MAX(0.0D0,D1))
      DT=MIN(0.999D0,MAX(0.0D0,DT))
C
C     Shear coupling of Ge Eq.3 uses the OPEN-crack damages: closed
C     crack faces still slide, so shear stiffness is not recovered.
      DS12=1.0D0-(1.0D0-D1)*(1.0D0-DT)
      DS23=1.0D0-(1.0D0-DT)*(1.0D0-DT)
      DS31=1.0D0-(1.0D0-DT)*(1.0D0-D1)
C
C     Unilateral crack closure on the normal directions.
      CALL KUNILAT(EPS(1),D1,HCLO,D1E)
      CALL KUNILAT(EPS(2),DT,HCLO,DT2E)
      CALL KUNILAT(EPS(3),DT,HCLO,DT3E)
      NCLO=0
      IF (EPS(1).LT.0.0D0) NCLO=NCLO+1
      IF (EPS(2).LT.0.0D0) NCLO=NCLO+1
      IF (EPS(3).LT.0.0D0) NCLO=NCLO+1
C
      CALL KORTHO(E1*(1.0D0-D1E),E2*(1.0D0-DT2E),E3*(1.0D0-DT3E),
     1     NU12*(1.0D0-D1E),NU13*(1.0D0-D1E),NU23*(1.0D0-DT2E),
     2     G12*(1.0D0-DS12),G13*(1.0D0-DS31),G23*(1.0D0-DS23),CD)
      DO I=1,6
         DO J=1,6
            CTAN(I,J)=CD(I,J)
         END DO
      END DO
      CALL KMATVEC6(CD,EPS,STRESS)
C
      MODE=1
      RFAC=R1T
      IF (R1C.GT.RFAC) THEN
         MODE=2
         RFAC=R1C
      END IF
      IF (RTT.GT.RFAC) THEN
         MODE=3
         RFAC=RTT
      END IF
      IF (RTC.GT.RFAC) THEN
         MODE=4
         RFAC=RTC
      END IF
      IF (SV(12).EQ.0.0D0 .AND. RFAC.GE.1.0D0) SV(12)=TEND
C
      SV(1)=D1T
      SV(2)=D1C
      SV(3)=DTT
      SV(4)=DTC
      SV(5)=R1T
      SV(6)=R1C
      SV(7)=RTT
      SV(8)=RTC
      SV(9)=D1
      SV(10)=DT
      SV(11)=DBLE(MODE)
      IF (NSTATV.GE.17) SV(17)=DBLE(NCLO)
C
      DJ=MAX(ABS(D1T-D1T0),ABS(D1C-D1C0),
     1       ABS(DTT-DTT0),ABS(DTC-DTC0))
      IF (DJMAX.GT.0.0D0 .AND. DJ.GT.CUTTRG*DJMAX) THEN
         REQ=CUTSAF*DJMAX/DJ
         IF (CUTMXF.GT.0.0D0) REQ=MIN(REQ,CUTMXF)
         REQ=MAX(PMIN,REQ)
         PNEWDT=MIN(PNEWDT,REQ)
         CREQ=SV(14)
         IF (CREQ.LE.0.0D0) CREQ=1.0D0
         SV(14)=MIN(CREQ,REQ)
      END IF
      IF (DJ.GT.SV(13)) THEN
         SV(13)=DJ
         SV(15)=TEND
         SV(16)=RFAC
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KMTRX31(EPS,STRESS,CTAN,SV,P,NT,DTIME,TEMP,DTEMP,
     1 PNEWDT,KSTEP,CELENT)
C     V1_0 KMTRX30 + temperature-dependent multipliers.  NT=0 reproduces
C     KMTRX30 exactly.  Unilateral behaviour is the sign(I1) switch of
C     Ge Eq.7, already present.
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      DOUBLE PRECISION C0(6,6),CD(6,6),EEL(6),EPL(6),STR(6),SD(6),F(3)
      DOUBLE PRECISION E,NU,XT,XC,AT,AC,DMAXT,DMAXC,ETA,DJMAX
      DOUBLE PRECISION FREEZE,PMIN,ENABLE,GMT,GMC,SY0,HISO
      DOUBLE PRECISION CUTTRG,CUTSAF,CUTMXF,REQ,CREQ
      DOUBLE PRECISION GMU,PBAR,QTR,SY,DLAM,PM,FAC
      DOUBLE PRECISION Q,AI1,FIT,FIC,RT,RC,DT0,DC0,DTN,DCN,TAR,GAM
      DOUBLE PRECISION BT,BC,DACT,DJ,TEND,RFAC
      INTEGER I,J,KSTEP,MODE,NT
C
      E=P(2)
      NU=P(3)
      XT=P(4)
      XC=P(5)
      AT=P(6)
      AC=P(7)
      DMAXT=P(8)
      DMAXC=P(9)
      ETA=P(10)
      DJMAX=P(11)
      FREEZE=P(12)
      PMIN=P(13)
      ENABLE=P(14)
      GMT=P(15)
      GMC=P(16)
      SY0=P(17)
      HISO=P(18)
      CUTTRG=MAX(1.0D0,P(19))
      CUTSAF=P(20)
      CUTMXF=P(21)
C
      TEND=TEMP+DTEMP
      CALL KPROP_INTERP(TEND,P,24,NT,3,F)
      E=E*F(1)
      HISO=HISO*F(1)
      XT=XT*F(2)
      XC=XC*F(2)
      SY0=SY0*F(3)
      GMU=E/(2.0D0*(1.0D0+NU))
C
      DO I=1,6
         EPL(I)=SV(14+I)
      END DO
      PBAR=SV(9)
      CALL KORTHO(E,E,E,NU,NU,NU,GMU,GMU,GMU,C0)
      DO I=1,6
         EEL(I)=EPS(I)-EPL(I)
      END DO
      CALL KMATVEC6(C0,EEL,STR)
C
      IF (SY0.GT.0.0D0 .AND. ENABLE.GT.0.5D0 .AND.
     1    DBLE(KSTEP).LE.FREEZE) THEN
         CALL KMISES(STR,QTR)
         SY=SY0+HISO*PBAR
         IF (QTR.GT.SY) THEN
            DLAM=(QTR-SY)/(3.0D0*GMU+HISO)
            PBAR=PBAR+DLAM
            PM=(STR(1)+STR(2)+STR(3))/3.0D0
            SD(1)=STR(1)-PM
            SD(2)=STR(2)-PM
            SD(3)=STR(3)-PM
            SD(4)=STR(4)
            SD(5)=STR(5)
            SD(6)=STR(6)
            FAC=1.5D0*DLAM/QTR
            DO I=1,3
               EPL(I)=EPL(I)+FAC*SD(I)
            END DO
            DO I=4,6
               EPL(I)=EPL(I)+2.0D0*FAC*SD(I)
            END DO
            DO I=1,6
               EEL(I)=EPS(I)-EPL(I)
            END DO
            CALL KMATVEC6(C0,EEL,STR)
         END IF
      END IF
C
      CALL KMISES(STR,Q)
      AI1=STR(1)+STR(2)+STR(3)
      FIT=0.0D0
      FIC=0.0D0
      IF (AI1.GE.0.0D0) THEN
         FIT=Q/XT
      ELSE
         FIC=Q/XC
      END IF
C
      DT0=MAX(0.0D0,MIN(DMAXT,SV(1)))
      DC0=MAX(0.0D0,MIN(DMAXC,SV(2)))
      RT=MAX(SV(3),FIT)
      RC=MAX(SV(4),FIC)
      DTN=DT0
      DCN=DC0
      CALL KABAND(XT*XT/(2.0D0*E)*CELENT,GMT,AT,BT)
      CALL KABAND(XC*XC/(2.0D0*E)*CELENT,GMC,AC,BC)
      IF (ENABLE.GT.0.5D0 .AND. DBLE(KSTEP).LE.FREEZE) THEN
         IF (ETA.GT.0.0D0) THEN
            GAM=DTIME/(ETA+DTIME)
         ELSE
            GAM=1.0D0
         END IF
         CALL KDAMAGE_TARGET(RT,BT,DMAXT,TAR)
         DTN=MAX(DT0,DT0+GAM*(TAR-DT0))
         CALL KDAMAGE_TARGET(RC,BC,DMAXC,TAR)
         DCN=MAX(DC0,DC0+GAM*(TAR-DC0))
      END IF
C
      IF (AI1.GE.0.0D0) THEN
         DACT=DTN
      ELSE
         DACT=DCN
      END IF
      DACT=MIN(0.999D0,MAX(0.0D0,DACT))
      CALL KORTHO(E*(1.0D0-DACT),E*(1.0D0-DACT),E*(1.0D0-DACT),
     1     NU*(1.0D0-DACT),NU*(1.0D0-DACT),NU*(1.0D0-DACT),
     2     GMU*(1.0D0-DACT),GMU*(1.0D0-DACT),GMU*(1.0D0-DACT),CD)
      DO I=1,6
         DO J=1,6
            CTAN(I,J)=CD(I,J)
         END DO
      END DO
      CALL KMATVEC6(CD,EEL,STRESS)
C
      MODE=1
      RFAC=RT
      IF (RC.GT.RFAC) THEN
         MODE=2
         RFAC=RC
      END IF
      IF (SV(8).EQ.0.0D0 .AND. RFAC.GE.1.0D0) SV(8)=TEND
      SV(1)=DTN
      SV(2)=DCN
      SV(3)=RT
      SV(4)=RC
      SV(5)=DACT
      SV(6)=SIGN(1.0D0,AI1)
      SV(7)=DBLE(MODE)
      SV(9)=PBAR
      SV(10)=BT
      DO I=1,6
         SV(14+I)=EPL(I)
      END DO
C
      DJ=MAX(ABS(DTN-DT0),ABS(DCN-DC0))
      IF (DJMAX.GT.0.0D0 .AND. DJ.GT.CUTTRG*DJMAX) THEN
         REQ=CUTSAF*DJMAX/DJ
         IF (CUTMXF.GT.0.0D0) REQ=MIN(REQ,CUTMXF)
         REQ=MAX(PMIN,REQ)
         PNEWDT=MIN(PNEWDT,REQ)
         CREQ=SV(12)
         IF (CREQ.LE.0.0D0) CREQ=1.0D0
         SV(12)=MIN(CREQ,REQ)
      END IF
      IF (DJ.GT.SV(11)) THEN
         SV(11)=DJ
         SV(13)=TEND
         SV(14)=RFAC
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KMACRO31(EPS,STRESS,CTAN,SV,P,NT,DTIME,TEMP,DTEMP,
     1 FLDV,PNEWDT,KSTEP,CELENT)
C     Homogenised orthotropic CDM for the macro scale.
C     Same 3-D Hashin + exponential-softening skeleton as the yarn law
C     (it is a general orthotropic CDM), driven by RVE-homogenised
C     stiffness and strengths, PLUS:
C       * unilateral crack closure (HCLO)
C       * cycle-dependent damage d_cyc with cycle-jump support
C     Without d_cyc this law shakes down after the first thermal cycle;
C     d_cyc is what makes repeated thermal shock degrade the material.
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,FLDV,PNEWDT,CELENT
      DOUBLE PRECISION C0(6,6),CD(6,6),SE(6),F(7)
      DOUBLE PRECISION E1,E2,E3,NU12,NU13,NU23,G12,G13,G23
      DOUBLE PRECISION XT,XC,YT,YC,S12,S13,S23
      DOUBLE PRECISION A1T,A1C,ATT,ATC,DMAX1,DMAXT,ETA,DJMAX
      DOUBLE PRECISION PMIN,ENABLE,FREEZE,CUTTRG,CUTSAF,CUTMXF
      DOUBLE PRECISION G1T,G1C,GTT,GTC,HCLO
      DOUBLE PRECISION CYCON,CCYC,CNEXP,CKEXP,RTH,DCYMAX,W1CYC
      DOUBLE PRECISION CYCRAT,RATE,DNINC
      DOUBLE PRECISION FI1T,FI1C,FITT,FITC,SUMT,TERM
      DOUBLE PRECISION R1T,R1C,RTT,RTC,TAR,GAM,TEND
      DOUBLE PRECISION D1T0,D1C0,DTT0,DTC0,D1T,D1C,DTT,DTC
      DOUBLE PRECISION D1M,DTM,D1,DT,D1E,DT2E,DT3E
      DOUBLE PRECISION DCY0,DCY,DDCY,EXC,DS12,DS23,DS31
      DOUBLE PRECISION DJ,RFAC,REQ,CREQ,B1T,B1C,BTT,BTC
      INTEGER I,J,KSTEP,MODE,NT,IPF,NCLO
C
      E1=P(2)
      E2=P(3)
      E3=P(4)
      NU12=P(5)
      NU13=P(6)
      NU23=P(7)
      G12=P(8)
      G13=P(9)
      G23=P(10)
      XT=P(11)
      XC=P(12)
      YT=P(13)
      YC=P(14)
      S12=P(15)
      S13=P(16)
      S23=P(17)
      A1T=P(18)
      A1C=P(19)
      ATT=P(20)
      ATC=P(21)
      DMAX1=P(22)
      DMAXT=P(23)
      ETA=P(24)
      DJMAX=P(25)
      FREEZE=P(26)
      PMIN=P(27)
      ENABLE=P(28)
      CUTTRG=MAX(1.0D0,P(29))
      CUTSAF=P(30)
      CUTMXF=P(31)
      G1T=P(32)
      G1C=P(33)
      GTT=P(34)
      GTC=P(35)
      HCLO=MIN(1.0D0,MAX(0.0D0,P(37)))
      CYCON=P(38)
      CCYC=P(39)
      CNEXP=P(40)
      CKEXP=P(41)
      RTH=P(42)
      DCYMAX=MIN(0.99D0,MAX(0.0D0,P(43)))
      W1CYC=MIN(1.0D0,MAX(0.0D0,P(44)))
      CYCRAT=P(45)
      IPF=NINT(P(46))
C
      TEND=TEMP+DTEMP
      CALL KPROP_INTERP(TEND,P,48,NT,7,F)
      E1=E1*F(1)
      E2=E2*F(2)
      E3=E3*F(2)
      G12=G12*F(3)
      G13=G13*F(3)
      G23=G23*F(3)
      XT=XT*F(4)
      XC=XC*F(4)
      YT=YT*F(5)
      YC=YC*F(5)
      S12=S12*F(6)
      S13=S13*F(6)
      S23=S23*F(6)
      CCYC=CCYC*F(7)
C
      CALL KORTHO(E1,E2,E3,NU12,NU13,NU23,G12,G13,G23,C0)
      CALL KMATVEC6(C0,EPS,SE)
C
      FI1T=0.0D0
      FI1C=0.0D0
      FITT=0.0D0
      FITC=0.0D0
      IF (SE(1).GE.0.0D0) THEN
         FI1T=SQRT((SE(1)/XT)**2+(SE(4)/S12)**2+
     1              (SE(5)/S13)**2)
      ELSE
         FI1C=ABS(SE(1))/XC
      END IF
      SUMT=SE(2)+SE(3)
      IF (SUMT.GE.0.0D0) THEN
         TERM=(SUMT/YT)**2+(SE(6)*SE(6)-SE(2)*SE(3))/
     1        (S23*S23)+(SE(4)/S12)**2+(SE(5)/S13)**2
         FITT=SQRT(MAX(0.0D0,TERM))
      ELSE
         TERM=((YC/(2.0D0*S23))**2-1.0D0)*SUMT/YC+
     1        (SUMT/(2.0D0*S23))**2+
     2        (SE(6)*SE(6)-SE(2)*SE(3))/(S23*S23)+
     3        (SE(4)/S12)**2+(SE(5)/S13)**2
         FITC=SQRT(MAX(0.0D0,TERM))
      END IF
C
      D1T0=MAX(0.0D0,MIN(DMAX1,SV(1)))
      D1C0=MAX(0.0D0,MIN(DMAX1,SV(2)))
      DTT0=MAX(0.0D0,MIN(DMAXT,SV(3)))
      DTC0=MAX(0.0D0,MIN(DMAXT,SV(4)))
      R1T=MAX(SV(5),FI1T)
      R1C=MAX(SV(6),FI1C)
      RTT=MAX(SV(7),FITT)
      RTC=MAX(SV(8),FITC)
      D1T=D1T0
      D1C=D1C0
      DTT=DTT0
      DTC=DTC0
      DCY0=MIN(DCYMAX,MAX(0.0D0,SV(17)))
      DCY=DCY0
C
      CALL KABAND(XT*XT/(2.0D0*E1)*CELENT,G1T,A1T,B1T)
      CALL KABAND(XC*XC/(2.0D0*E1)*CELENT,G1C,A1C,B1C)
      CALL KABAND(YT*YT/(2.0D0*E2)*CELENT,GTT,ATT,BTT)
      CALL KABAND(YC*YC/(2.0D0*E2)*CELENT,GTC,ATC,BTC)
C
      IF (ENABLE.GT.0.5D0 .AND. DBLE(KSTEP).LE.FREEZE) THEN
         IF (ETA.GT.0.0D0) THEN
            GAM=DTIME/(ETA+DTIME)
         ELSE
            GAM=1.0D0
         END IF
         CALL KDAMAGE_TARGET(R1T,B1T,DMAX1,TAR)
         D1T=MAX(D1T0,D1T0+GAM*(TAR-D1T0))
         CALL KDAMAGE_TARGET(R1C,B1C,DMAX1,TAR)
         D1C=MAX(D1C0,D1C0+GAM*(TAR-D1C0))
         CALL KDAMAGE_TARGET(RTT,BTT,DMAXT,TAR)
         DTT=MAX(DTT0,DTT0+GAM*(TAR-DTT0))
         CALL KDAMAGE_TARGET(RTC,BTC,DMAXT,TAR)
         DTC=MAX(DTC0,DTC0+GAM*(TAR-DTC0))
      END IF
C
      D1M=1.0D0-(1.0D0-D1T)*(1.0D0-D1C)
      DTM=1.0D0-(1.0D0-DTT)*(1.0D0-DTC)
      D1M=MIN(0.999D0,MAX(0.0D0,D1M))
      DTM=MIN(0.999D0,MAX(0.0D0,DTM))
C
      MODE=1
      RFAC=R1T
      IF (R1C.GT.RFAC) THEN
         MODE=2
         RFAC=R1C
      END IF
      IF (RTT.GT.RFAC) THEN
         MODE=3
         RFAC=RTT
      END IF
      IF (RTC.GT.RFAC) THEN
         MODE=4
         RFAC=RTC
      END IF
C
C     Cycle-dependent damage.  Driven by the CURRENT failure index of
C     this increment (not the stored threshold), so a load reversal that
C     never re-exceeds the historical maximum still accumulates damage.
      RATE=0.0D0
      DNINC=0.0D0
      IF (CYCON.GT.0.5D0 .AND. ENABLE.GT.0.5D0 .AND.
     1    DBLE(KSTEP).LE.FREEZE) THEN
         IF (IPF.GT.0) THEN
            RATE=FLDV
         ELSE
            RATE=CYCRAT
         END IF
         IF (RATE.GT.0.0D0 .AND. DTIME.GT.0.0D0) THEN
            DNINC=RATE*DTIME
            EXC=MAX(FI1T,FI1C,FITT,FITC)-RTH
            IF (EXC.GT.0.0D0 .AND. CCYC.GT.0.0D0) THEN
               DDCY=CCYC*(EXC**CNEXP)*
     1              ((1.0D0-DCY0)**(-CKEXP))*DNINC
               DDCY=MAX(0.0D0,MIN(DDCY,DCYMAX))
               DCY=MIN(DCYMAX,DCY0+DDCY)
            END IF
         END IF
      END IF
C
C     Multiplicative coupling: 1-d = (1-d_mono)(1-w*d_cyc).
      D1=1.0D0-(1.0D0-D1M)*(1.0D0-W1CYC*DCY)
      DT=1.0D0-(1.0D0-DTM)*(1.0D0-DCY)
      D1=MIN(0.999D0,MAX(0.0D0,D1))
      DT=MIN(0.999D0,MAX(0.0D0,DT))
C
      DS12=1.0D0-(1.0D0-D1)*(1.0D0-DT)
      DS23=1.0D0-(1.0D0-DT)*(1.0D0-DT)
      DS31=1.0D0-(1.0D0-DT)*(1.0D0-D1)
C
      CALL KUNILAT(EPS(1),D1,HCLO,D1E)
      CALL KUNILAT(EPS(2),DT,HCLO,DT2E)
      CALL KUNILAT(EPS(3),DT,HCLO,DT3E)
      NCLO=0
      IF (EPS(1).LT.0.0D0) NCLO=NCLO+1
      IF (EPS(2).LT.0.0D0) NCLO=NCLO+1
      IF (EPS(3).LT.0.0D0) NCLO=NCLO+1
C
      CALL KORTHO(E1*(1.0D0-D1E),E2*(1.0D0-DT2E),E3*(1.0D0-DT3E),
     1     NU12*(1.0D0-D1E),NU13*(1.0D0-D1E),NU23*(1.0D0-DT2E),
     2     G12*(1.0D0-DS12),G13*(1.0D0-DS31),G23*(1.0D0-DS23),CD)
      DO I=1,6
         DO J=1,6
            CTAN(I,J)=CD(I,J)
         END DO
      END DO
      CALL KMATVEC6(CD,EPS,STRESS)
C
      IF (SV(12).EQ.0.0D0 .AND. RFAC.GE.1.0D0) SV(12)=TEND
      SV(1)=D1T
      SV(2)=D1C
      SV(3)=DTT
      SV(4)=DTC
      SV(5)=R1T
      SV(6)=R1C
      SV(7)=RTT
      SV(8)=RTC
      SV(9)=D1
      SV(10)=DT
      SV(11)=DBLE(MODE)
      SV(17)=DCY
      SV(18)=SV(18)+DNINC
      SV(19)=MAX(FI1T,FI1C,FITT,FITC)
      SV(20)=D1M
      SV(21)=DTM
      SV(22)=DBLE(NCLO)
C
      DJ=MAX(ABS(D1T-D1T0),ABS(D1C-D1C0),
     1       ABS(DTT-DTT0),ABS(DTC-DTC0),ABS(DCY-DCY0))
      IF (DJMAX.GT.0.0D0 .AND. DJ.GT.CUTTRG*DJMAX) THEN
         REQ=CUTSAF*DJMAX/DJ
         IF (CUTMXF.GT.0.0D0) REQ=MIN(REQ,CUTMXF)
         REQ=MAX(PMIN,REQ)
         PNEWDT=MIN(PNEWDT,REQ)
         CREQ=SV(14)
         IF (CREQ.LE.0.0D0) CREQ=1.0D0
         SV(14)=MIN(CREQ,REQ)
      END IF
      IF (DJ.GT.SV(13)) THEN
         SV(13)=DJ
         SV(15)=TEND
         SV(16)=RFAC
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KPROP_INTERP(TQ,P,I0,NT,NV,F)
C     Piecewise-linear interpolation of NV multiplier curves stored in
C     P starting at slot I0 as NT consecutive rows of (1+NV) numbers:
C        T_j, f_1j, ..., f_NVj        with T_j strictly ascending.
C     CLAMPED outside the table -- multipliers are never extrapolated,
C     because extrapolated stiffness/strength is the classic source of
C     nonsense at temperatures the data does not cover.
C     NT<=0 returns f=1 (temperature-independent, i.e. V1_0 behaviour).
      IMPLICIT NONE
      DOUBLE PRECISION TQ,P(*),F(*)
      DOUBLE PRECISION TA,TB,W
      INTEGER I0,NT,NV,J,K,IA,IB,NR
      DO K=1,NV
         F(K)=1.0D0
      END DO
      IF (NT.LE.0) RETURN
      NR=1+NV
      IA=I0
      IF (NT.EQ.1 .OR. TQ.LE.P(IA)) THEN
         DO K=1,NV
            F(K)=MAX(1.0D-6,P(IA+K))
         END DO
         RETURN
      END IF
      IB=I0+(NT-1)*NR
      IF (TQ.GE.P(IB)) THEN
         DO K=1,NV
            F(K)=MAX(1.0D-6,P(IB+K))
         END DO
         RETURN
      END IF
      DO J=1,NT-1
         IA=I0+(J-1)*NR
         IB=IA+NR
         TA=P(IA)
         TB=P(IB)
         IF (TQ.GE.TA .AND. TQ.LE.TB) THEN
            IF (TB-TA.LE.1.0D-12) THEN
               W=0.0D0
            ELSE
               W=(TQ-TA)/(TB-TA)
            END IF
            DO K=1,NV
               F(K)=MAX(1.0D-6,P(IA+K)+W*(P(IB+K)-P(IA+K)))
            END DO
            RETURN
         END IF
      END DO
      RETURN
      END
C=======================================================================
      SUBROUTINE KUNILAT(EPSN,D,HCLO,DEFF)
C     Unilateral (crack-closure) deactivation of damage.
C       eps_n >= 0 : crack open   -> full damage
C       eps_n <  0 : crack closed -> damage reduced by the recovery
C                    fraction HCLO
C     HCLO=0 -> no recovery (V1_0 behaviour); HCLO=1 -> full recovery.
C     History is NOT modified here; only the secant stiffness changes.
      IMPLICIT NONE
      DOUBLE PRECISION EPSN,D,HCLO,DEFF
      IF (EPSN.GE.0.0D0) THEN
         DEFF=D
      ELSE
         DEFF=D*(1.0D0-HCLO)
      END IF
      DEFF=MIN(0.999D0,MAX(0.0D0,DEFF))
      RETURN
      END
C=======================================================================
      SUBROUTINE KMIX1T(R,A,E1,XT,XPO,RFT,XK1,D)
C     Mixed linear-exponential law for yarn 1t (Zhang Eq.18 with the
C     auxiliary variables of Ge Eqs.16-17).
      IMPLICIT NONE
      DOUBLE PRECISION R,A,E1,XT,XPO,RFT,XK1,D
      DOUBLE PRECISION RL,DL,DF,RE,C1
      IF (R.LE.1.0D0) THEN
         D=0.0D0
         RETURN
      END IF
      C1=1.0D0+XK1/E1
      RL=MAX(1.0D0,MIN(R,RFT))
      DL=C1*(1.0D0-1.0D0/RL)
      DF=C1*(1.0D0-1.0D0/RFT)
      RE=MAX(1.0D0,(1.0D0-DF)*(XT/XPO)*R)
      D=1.0D0-(1.0D0-DL)/RE*EXP(A*(1.0D0-RE))
      D=MIN(0.999D0,MAX(0.0D0,D))
      RETURN
      END
C=======================================================================
      SUBROUTINE KABAND(G0LE,GF,AFIX,A)
C     Crack-band softening factor (Ge Eqs.19-21 closed form for the
C     exponential law): A = 2*g0*le/(Gf-g0*le). Snap-back clamp 50.
      IMPLICIT NONE
      DOUBLE PRECISION G0LE,GF,AFIX,A
      IF (GF.LE.0.0D0) THEN
         A=AFIX
         RETURN
      END IF
      IF (GF.GT.1.02D0*G0LE) THEN
         A=2.0D0*G0LE/(GF-G0LE)
      ELSE
         A=50.0D0
      END IF
      A=MIN(50.0D0,MAX(1.0D-2,A))
      RETURN
      END
C=======================================================================
      SUBROUTINE KDAMAGE_TARGET(R,A,DMAX,D)
C     Exponential law d = 1 - exp[A(1-r)]/r (Zhang Eqs.17 and 19).
      IMPLICIT NONE
      DOUBLE PRECISION R,A,DMAX,D
      IF (R.LE.1.0D0) THEN
         D=0.0D0
      ELSE
         D=1.0D0-EXP(A*(1.0D0-R))/R
         D=MIN(DMAX,MAX(0.0D0,D))
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KORTHO(E1,E2,E3,N12,N13,N23,G12,G13,G23,C)
      IMPLICIT NONE
      DOUBLE PRECISION E1,E2,E3,N12,N13,N23,G12,G13,G23
      DOUBLE PRECISION C(6,6),S11,S22,S33,S12,S13,S23,DET
      INTEGER I,J
      DO I=1,6
         DO J=1,6
            C(I,J)=0.0D0
         END DO
      END DO
      S11=1.0D0/E1
      S22=1.0D0/E2
      S33=1.0D0/E3
      S12=-N12/E1
      S13=-N13/E1
      S23=-N23/E2
      DET=S11*S22*S33+2.0D0*S12*S13*S23-
     1    S11*S23*S23-S22*S13*S13-S33*S12*S12
      IF (DET.LE.1.0D-30) THEN
         WRITE(7,*) 'Invalid orthotropic elastic constants; det=',DET
         CALL XIT
      END IF
      C(1,1)=(S22*S33-S23*S23)/DET
      C(2,2)=(S11*S33-S13*S13)/DET
      C(3,3)=(S11*S22-S12*S12)/DET
      C(1,2)=(S13*S23-S12*S33)/DET
      C(2,1)=C(1,2)
      C(1,3)=(S12*S23-S13*S22)/DET
      C(3,1)=C(1,3)
      C(2,3)=(S12*S13-S11*S23)/DET
      C(3,2)=C(2,3)
      C(4,4)=G12
      C(5,5)=G13
      C(6,6)=G23
      RETURN
      END
C=======================================================================
      SUBROUTINE KMATVEC6(A,X,Y)
      IMPLICIT NONE
      DOUBLE PRECISION A(6,6),X(6),Y(6)
      INTEGER I,J
      DO I=1,6
         Y(I)=0.0D0
         DO J=1,6
            Y(I)=Y(I)+A(I,J)*X(J)
         END DO
      END DO
      RETURN
      END
C=======================================================================
      SUBROUTINE KMISES(S,Q)
      IMPLICIT NONE
      DOUBLE PRECISION S(6),Q
      Q=SQRT(MAX(0.0D0,0.5D0*((S(1)-S(2))**2+
     1 (S(2)-S(3))**2+(S(3)-S(1))**2)+
     2 3.0D0*(S(4)**2+S(5)**2+S(6)**2)))
      RETURN
      END
