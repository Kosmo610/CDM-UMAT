C=======================================================================
C  UMAT_CSIC_RVE_ZHANG2022_V1_0.for
C
C  Dedicated replication UMAT for:
C   Zhang et al. 2022 Ceramics International 48:3109-3124
C   "Effect of thermal residual stress on the tensile properties and
C    damage process of C/SiC composites at high temperatures"
C  Model equations that Zhang defers to Ref.[17] are taken from:
C   Ge et al. 2018 Compos. Sci. Technol. 157:86-98 (project file B01).
C
C  This is a NEW lineage. The thesis-line UMAT_CSIC_RVE_DAMAGE_V2_2
C  stays untouched (surgical principle).
C
C  YARN (CMNAME contains 'YARN')  -- transversely isotropic elastic
C    damage per Zhang Eqs.(1)-(5) and (11)-(14) and (17)-(18):
C    * Effective stress  s~ = C0 : eps            (Ge Eq.4)
C    * 3-D Hashin initiation, alpha=beta=1        (Zhang Eqs.11-14)
C    * Exponential evolution d=1-exp[A(1-r)]/r    (Zhang Eq.17)
C    * Mixed linear-exponential law for 1t        (Zhang Eq.18 with
C      the auxiliary variables of Ge Eqs.16-17: K1, rF, X_PO)
C    * Shear damage coupling d4,d5,d6             (Ge Eq.3)
C    * Compliance-based degradation S(d)          (Ge Eq.2)
C    * Optional crack-band regularization of A    (Ge Eqs.19-21)
C
C  MATRIX (CMNAME contains 'MATRIX') -- isotropic coupled
C    elastic-plastic damage per Zhang Eqs.(6)-(10) and (15)-(16),(19):
C    * s~ = C0 : (eps - eps_p)                    (Ge Eq.6)
C    * von Mises plasticity in the EFFECTIVE stress space with
C      associated flow and linear isotropic hardening
C      sy = SY0 + HISO*pbar  (radial return)      (Ge Eqs.8-9)
C    * Initiation: vM(s~)/Xt if I1>=0 else vM/Xc  (Zhang Eqs.15-16)
C    * Exponential evolution                      (Zhang Eq.19)
C    * Compliance-based isotropic degradation with tension or
C      compression damage active by sign of I1(s~) (Ge Eq.7)
C    * Optional crack-band regularization of Am,t and Am,c
C
C  Thermal strain is supplied by Abaqus *EXPANSION (zero=1050).
C  STRAN/DSTRAN entering the UMAT are therefore mechanical strains.
C  Jacobian = damaged secant stiffness. Viscous regularization eta
C  plus damage-jump cutback control give robustness (V2_2 machinery).
C
C  MATRIX PROPS (NPROPS=22)                YARN PROPS (NPROPS=38)
C   1 phase id                              1 phase id
C   2 E      3 nu                           2-10 E1 E2 E3 n12 n13 n23
C   4 Xt     5 Xc                                G12 G13 G23
C   6 At     7 Ac   (used when G<=0)       11-17 Xt Xc Yt Yc S12 S13 S23
C   8 dmax_t 9 dmax_c                      18-21 A1t A1c Att Atc
C  10 eta   11 max_djump                   22 dmax_1  23 dmax_t
C  12 freeze_step  13 min_PNEWDT           24 eta     25 max_djump
C  14 enable                               26 freeze  27 min_PNEWDT
C  15 Gm_t  16 Gm_c  (N/mm; 0=off)         28 enable
C  17 SY0   18 HISO  (SY0<=0: no plast.)   29-31 cut trig/safety/maxf
C  19-21 cut trig/safety/maxf              32-35 G1t G1c Gtt Gtc (N/mm)
C  22 CARD KEY = 30.0 (guard)              36 X_PO  37 rF  38 K1
C                                             (X_PO<=0: Eq.17 for 1t)
C  MATRIX NSTATV=20: 1 DMT 2 DMC 3 RMT 4 RMC 5 DACT 6 I1SGN 7 MODE
C   8 TMINIT 9 EQPS 10 ATEFF 11 DJUMP 12 CUTREQ 13 TJUMP 14 RJUMP
C   15-20 plastic strain (11 22 33 12 13 23, engineering shears)
C  YARN NSTATV=16: identical layout and names as V2_2.
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
      DOUBLE PRECISION EPS(6),SOLD(6),SSEOLD,SPDOLD,WORK,DW
      INTEGER I,J
C
      IF (NTENS.NE.6 .OR. NDI.NE.3 .OR. NSHR.NE.3) THEN
         WRITE(7,*) 'ZHANG2022 UMAT: 3-D solid elements only.'
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
      IF (INDEX(CMNAME,'YARN').GT.0) THEN
         IF (NPROPS.NE.38 .OR. NSTATV.LT.16) THEN
            WRITE(7,*) 'ZHANG2022 YARN card needs NPROPS=38 and'
            WRITE(7,*) 'NSTATV>=16. Got NPROPS,NSTATV=',NPROPS,NSTATV
            CALL XIT
         END IF
         CALL KYARN30(EPS,STRESS,DDSDDE,STATEV,PROPS,
     1        DTIME,TEMP,DTEMP,PNEWDT,KSTEP,CELENT)
      ELSE IF (INDEX(CMNAME,'MATRIX').GT.0) THEN
         IF (NPROPS.NE.22 .OR. NSTATV.LT.20 .OR.
     1       ABS(PROPS(22)-30.0D0).GT.1.0D-6) THEN
            WRITE(7,*) 'ZHANG2022 MATRIX card needs NPROPS=22 with'
            WRITE(7,*) 'PROPS(22)=30.0 as key and NSTATV>=20.'
            WRITE(7,*) 'Got NPROPS,NSTATV=',NPROPS,NSTATV
            WRITE(7,*) 'A V2_x-lineage card was likely supplied.'
            CALL XIT
         END IF
         CALL KMTRX30(EPS,STRESS,DDSDDE,STATEV,PROPS,
     1        DTIME,TEMP,DTEMP,PNEWDT,KSTEP,CELENT)
      ELSE
         WRITE(7,*) 'Unknown CMNAME in ZHANG2022 UMAT: ',CMNAME
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
      SUBROUTINE KYARN30(EPS,STRESS,CTAN,SV,P,DTIME,TEMP,DTEMP,
     1 PNEWDT,KSTEP,CELENT)
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      DOUBLE PRECISION C0(6,6),CD(6,6),SE(6)
      DOUBLE PRECISION E1,E2,E3,NU12,NU13,NU23,G12,G13,G23
      DOUBLE PRECISION XT,XC,YT,YC,S12,S13,S23
      DOUBLE PRECISION A1T,A1C,ATT,ATC,DMAX1,DMAXT,ETA,DJMAX
      DOUBLE PRECISION PMIN,ENABLE,FREEZE,CUTTRG,CUTSAF,CUTMXF
      DOUBLE PRECISION G1T,G1C,GTT,GTC,XPO,RFT,XK1
      DOUBLE PRECISION FI1T,FI1C,FITT,FITC,SUMT,TERM
      DOUBLE PRECISION R1T,R1C,RTT,RTC,TAR,GAM
      DOUBLE PRECISION D1T0,D1C0,DTT0,DTC0,D1T,D1C,DTT,DTC
      DOUBLE PRECISION D1,DT,DS12,DS23,DS31,DJ,TEND,RFAC,REQ,CREQ
      DOUBLE PRECISION B1T,B1C,BTT,BTC
      INTEGER I,J,KSTEP,MODE
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
C     Per-mode softening factor. Crack-band value when G>0 (Ge
C     Eqs.19-21 closed form) else the fixed PROPS value.
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
C     Shear coupling of Ge Eq.3 with d2=d3=DT:
C       d4(12)=1-(1-d1)(1-d2)  d5(23)=1-(1-d2)(1-d3)
C       d6(31)=1-(1-d3)(1-d1)
      DS12=1.0D0-(1.0D0-D1)*(1.0D0-DT)
      DS23=1.0D0-(1.0D0-DT)*(1.0D0-DT)
      DS31=1.0D0-(1.0D0-DT)*(1.0D0-D1)
C
C     Compliance-based degradation of Ge Eq.2. Equivalent to an
C     orthotropic build with Ei(1-di) and nu_ij scaled by (1-d_i)
C     so that the off-diagonal compliances -nu_ij/E_i stay intact.
C     Abaqus order: 4=12 5=13 6=23.
      CALL KORTHO(E1*(1.0D0-D1),E2*(1.0D0-DT),E3*(1.0D0-DT),
     1     NU12*(1.0D0-D1),NU13*(1.0D0-D1),NU23*(1.0D0-DT),
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
      TEND=TEMP+DTEMP
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
      SUBROUTINE KMTRX30(EPS,STRESS,CTAN,SV,P,DTIME,TEMP,DTEMP,
     1 PNEWDT,KSTEP,CELENT)
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      DOUBLE PRECISION C0(6,6),CD(6,6),EEL(6),EPL(6),STR(6),SD(6)
      DOUBLE PRECISION E,NU,XT,XC,AT,AC,DMAXT,DMAXC,ETA,DJMAX
      DOUBLE PRECISION FREEZE,PMIN,ENABLE,GMT,GMC,SY0,HISO
      DOUBLE PRECISION CUTTRG,CUTSAF,CUTMXF,REQ,CREQ
      DOUBLE PRECISION GMU,PBAR,QTR,SY,DLAM,PM,FAC
      DOUBLE PRECISION Q,AI1,FIT,FIC,RT,RC,DT0,DC0,DTN,DCN,TAR,GAM
      DOUBLE PRECISION BT,BC,DACT,DJ,TEND,RFAC
      INTEGER I,J,KSTEP,MODE
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
C     von Mises radial return in the effective stress space with
C     linear isotropic hardening (Ge Eqs.8-9). Exact one step.
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
C     Initiation criteria of Zhang Eqs.15-16 on the effective stress.
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
C     Ge Eq.7: tension or compression damage active by sign of I1.
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
      TEND=TEMP+DTEMP
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
      SUBROUTINE KMIX1T(R,A,E1,XT,XPO,RFT,XK1,D)
C     Mixed linear-exponential law for yarn 1t (Zhang Eq.18 with the
C     auxiliary variables of Ge Eqs.16-17):
C       rL = max(1,min(r,rF));  dL = (1+K1/E1)*(1-1/rL)
C       dF = (1+K1/E1)*(1-1/rF)
C       rE = max(1,(1-dF)*(Xt/X_PO)*r)
C       d  = 1-(1-dL)/rE*exp[A(1-rE)]
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
C     GF<=0 returns the fixed factor AFIX.
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
