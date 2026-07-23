C     Single material-point driver to verify UMAT_CSIC_ZHANG2022_V3_1_FAST
      PROGRAM DRIVER
      IMPLICIT REAL*8(A-H,O-Z)
      EXTERNAL UMAT
      WRITE(*,*) '================ MATRIX uniaxial tension ================'
      CALL RUNMAT()
      WRITE(*,*) ''
      WRITE(*,*) '================ YARN longitudinal tension ============='
      CALL RUNYARN()
      WRITE(*,*) ''
      WRITE(*,*) '================ TANGENT finite-diff check ============='
      CALL TANCHK()
      END
C-----------------------------------------------------------------------
      SUBROUTINE MATPROP(P)
      IMPLICIT REAL*8(A-H,O-Z)
      DIMENSION P(31)
      P(1)=2.0D0
      P(2)=350000.D0
      P(3)=0.2D0
      P(4)=310.D0
      P(5)=310.D0
      P(6)=100.D0
      P(7)=120000.D0
      P(8)=2.D0
      P(9)=2.D0
      P(10)=1.D-6
      P(11)=0.03D0
      P(12)=0.2D0
      P(13)=1.0D0
      P(14)=0.999D0
      P(15)=0.0D0
      RETURN
      END
C-----------------------------------------------------------------------
      SUBROUTINE YRNPROP(P)
      IMPLICIT REAL*8(A-H,O-Z)
      DIMENSION P(31)
      P(1)=1.0D0
      P(2)=254967.228D0
      P(3)=44321.7376D0
      P(4)=44321.7376D0
      P(5)=0.247516386D0
      P(6)=0.247516386D0
      P(7)=0.389940281D0
      P(8)=26431.5153D0
      P(9)=26431.5153D0
      P(10)=15876.668D0
      P(11)=3968.62033D0
      P(12)=2738.12632D0
      P(13)=545.37343D0
      P(14)=545.37343D0
      P(15)=464.384723D0
      P(16)=464.384723D0
      P(17)=136.343358D0
      P(18)=2.D0
      P(19)=2.D0
      P(20)=2.D0
      P(21)=2.D0
      P(22)=50993.4456D0
      P(23)=1.5D0
      P(24)=0.4D0
      P(25)=3571.7583D0
      P(26)=1.D-6
      P(27)=0.03D0
      P(28)=0.2D0
      P(29)=1.0D0
      P(30)=0.999D0
      P(31)=0.0D0
      RETURN
      END
C-----------------------------------------------------------------------
      SUBROUTINE CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,
     1     PROPS,NSTATV,NPROPS,PNEWDT)
      IMPLICIT REAL*8(A-H,O-Z)
      CHARACTER*80 CMNAME
      DIMENSION STRESS(6),STATEV(NSTATV),DDSDDE(6,6),DDSDDT(6),
     1  DRPLDE(6),STRAN(6),DSTRAN(6),TIME(2),PREDEF(1),DPRED(1),
     2  PROPS(NPROPS),COORDS(3),DROT(3,3),DFGRD0(3,3),DFGRD1(3,3)
      SSE=0.D0
      SPD=0.D0
      SCD=0.D0
      RPL=0.D0
      DRPLDT=0.D0
      DTIME=1.0D0
      TEMP=23.D0
      DTEMP=0.D0
      TIME(1)=0.D0
      TIME(2)=0.D0
      CELENT=1.0D0
      DO I=1,3
        COORDS(I)=0.D0
        DO J=1,3
          DROT(I,J)=0.D0
          DFGRD0(I,J)=0.D0
          DFGRD1(I,J)=0.D0
        END DO
        DROT(I,I)=1.D0
        DFGRD0(I,I)=1.D0
        DFGRD1(I,I)=1.D0
      END DO
      PNEWDT=1.0D0
      CALL UMAT(STRESS,STATEV,DDSDDE,SSE,SPD,SCD,
     1 RPL,DDSDDT,DRPLDE,DRPLDT,STRAN,DSTRAN,TIME,DTIME,TEMP,
     2 DTEMP,PREDEF,DPRED,CMNAME,3,3,6,NSTATV,PROPS,
     3 NPROPS,COORDS,DROT,PNEWDT,CELENT,DFGRD0,DFGRD1,
     4 1,1,1,1,1,1)
      RETURN
      END
C-----------------------------------------------------------------------
C     Uniaxial STRESS state via strain control: pull eps11, let lateral
C     strains relax to keep s22=s33=0 (simple secant iteration per step).
      SUBROUTINE RUNMAT()
      IMPLICIT REAL*8(A-H,O-Z)
      CHARACTER*80 CMNAME
      DIMENSION STRESS(6),STATEV(14),DDSDDE(6,6),STRAN(6),DSTRAN(6),
     1  P(31),E2(6)
      CMNAME='SIC_MATRIX_DAMAGE'
      CALL MATPROP(P)
      DO I=1,6
        STRESS(I)=0.D0
        STRAN(I)=0.D0
      END DO
      DO I=1,14
        STATEV(I)=0.D0
      END DO
      NSTEP=400
      DEPS=1.5D-2/DBLE(NSTEP)
      EY=0.D0
      EZ=0.D0
      SMAX=0.D0
      WRITE(*,'(A)') '   eps11      sig11      DM       PEEQ'
      DO K=1,NSTEP
C       inner iterations to null lateral stress (transverse free)
        DO IT=1,40
          DSTRAN(1)=DEPS
          DSTRAN(2)=EY-STRAN(2)
          DSTRAN(3)=EZ-STRAN(3)
          DSTRAN(4)=0.D0
          DSTRAN(5)=0.D0
          DSTRAN(6)=0.D0
          DO I=1,6
            E2(I)=STRESS(I)
          END DO
          CALL SAVEST(STATEV,14)
          CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,14,31,
     1               PNEWDT)
          CALL RESTST(STATEV,14)
C         Newton on lateral strains to drive s22,s33 -> 0
          C22=DDSDDE(2,2)
          IF (C22.LT.1.D0) C22=1.D0
          EY=EY-STRESS(2)/C22
          EZ=EZ-STRESS(3)/C22
          IF (ABS(STRESS(2))+ABS(STRESS(3)).LT.1.D-4) GOTO 10
          DO I=1,6
            STRESS(I)=E2(I)
          END DO
        END DO
   10   CONTINUE
C       accept step
        CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,14,31,
     1             PNEWDT)
        DO I=1,6
          STRAN(I)=STRAN(I)+DSTRAN(I)
        END DO
        IF (STRESS(1).GT.SMAX) SMAX=STRESS(1)
        IF (MOD(K,40).EQ.0) THEN
          WRITE(*,'(F9.5,F11.3,F9.4,F10.6)') STRAN(1),STRESS(1),
     1        STATEV(14),STATEV(7)
        END IF
      END DO
      WRITE(*,'(A,F10.3,A)') ' peak matrix sig11 = ',SMAX,' MPa'
      WRITE(*,'(A,F10.1,A)') ' initial slope E    = ',350000.D0,' (E)'
      RETURN
      END
C-----------------------------------------------------------------------
      SUBROUTINE RUNYARN()
      IMPLICIT REAL*8(A-H,O-Z)
      CHARACTER*80 CMNAME
      DIMENSION STRESS(6),STATEV(12),DDSDDE(6,6),STRAN(6),DSTRAN(6),
     1  P(31),E2(6)
      CMNAME='CSIC_YARN_DAMAGE'
      CALL YRNPROP(P)
      DO I=1,6
        STRESS(I)=0.D0
        STRAN(I)=0.D0
      END DO
      DO I=1,12
        STATEV(I)=0.D0
      END DO
      NSTEP=400
      DEPS=3.0D-2/DBLE(NSTEP)
      EY=0.D0
      EZ=0.D0
      SMAX=0.D0
      WRITE(*,'(A)') '   eps11      sig11      DYL      DYT'
      DO K=1,NSTEP
        DO IT=1,40
          DSTRAN(1)=DEPS
          DSTRAN(2)=EY-STRAN(2)
          DSTRAN(3)=EZ-STRAN(3)
          DSTRAN(4)=0.D0
          DSTRAN(5)=0.D0
          DSTRAN(6)=0.D0
          DO I=1,6
            E2(I)=STRESS(I)
          END DO
          CALL SAVEST(STATEV,12)
          CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,12,31,
     1               PNEWDT)
          CALL RESTST(STATEV,12)
          C22=DDSDDE(2,2)
          IF (C22.LT.1.D0) C22=1.D0
          EY=EY-STRESS(2)/C22
          EZ=EZ-STRESS(3)/C22
          IF (ABS(STRESS(2))+ABS(STRESS(3)).LT.1.D-3) GOTO 10
          DO I=1,6
            STRESS(I)=E2(I)
          END DO
        END DO
   10   CONTINUE
        CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,12,31,
     1             PNEWDT)
        DO I=1,6
          STRAN(I)=STRAN(I)+DSTRAN(I)
        END DO
        IF (STRESS(1).GT.SMAX) SMAX=STRESS(1)
        IF (MOD(K,40).EQ.0) THEN
          WRITE(*,'(F9.5,F11.2,F9.4,F9.4)') STRAN(1),STRESS(1),
     1        STATEV(1),STATEV(2)
        END IF
      END DO
      WRITE(*,'(A,F10.2,A)') ' peak yarn sig11 = ',SMAX,' MPa'
      RETURN
      END
C-----------------------------------------------------------------------
C     Consistent-tangent finite-difference check.
C     Probes dSIGMA/dDSTRAN about a nonzero REFERENCE increment applied
C     from a frozen state n, and compares to the returned DDSDDE at that
C     same reference increment (this is exactly what DDSDDE represents).
      SUBROUTINE TANCHK()
      IMPLICIT REAL*8(A-H,O-Z)
      WRITE(*,'(A)') ' [A] Elastic regime (tiny increment, no yield):'
      CALL TANONE(1.0D-6,-2.0D-7,-2.0D-7,0.D0,ERA)
      WRITE(*,'(A,F10.5,A)') '     relative tangent error = ',ERA,' %'
      WRITE(*,'(A)') ' [B] Active plastic regime (no damage yet):'
      CALL TANONE(8.0D-4,-2.0D-4,-2.0D-4,0.D0,ERB)
      WRITE(*,'(A,F10.5,A)') '     relative tangent error = ',ERB,' %'
      WRITE(*,'(A)') ' [C] Plastic + shear coupling:'
      CALL TANONE(8.0D-4,-1.0D-4,-1.0D-4,3.0D-4,ERC)
      WRITE(*,'(A,F10.5,A)') '     relative tangent error = ',ERC,' %'
      RETURN
      END
C-----------------------------------------------------------------------
      SUBROUTINE TANONE(D1,D2,D3,D4,RELERR)
      IMPLICIT REAL*8(A-H,O-Z)
      CHARACTER*80 CMNAME
      DIMENSION STRESS(6),STATEV(14),DDSDDE(6,6),STRAN(6),DSTRAN(6),
     1  P(31),ST0(14),SR0(6),DREF(6),SP(6),SM(6),CNUM(6,6),CANA(6,6)
      CMNAME='SIC_MATRIX_DAMAGE'
      CALL MATPROP(P)
C     Bring the point to a frozen state n (some prior plastic history).
      DO I=1,6
        STRESS(I)=0.D0
        STRAN(I)=0.D0
      END DO
      DO I=1,14
        STATEV(I)=0.D0
      END DO
      DSTRAN(1)=5.0D-4
      DSTRAN(2)=-1.0D-4
      DSTRAN(3)=-1.0D-4
      DSTRAN(4)=0.D0
      DSTRAN(5)=0.D0
      DSTRAN(6)=0.D0
      CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,14,31,PNEWDT)
      DO I=1,6
        STRAN(I)=STRAN(I)+DSTRAN(I)
        SR0(I)=STRESS(I)
      END DO
      DO I=1,14
        ST0(I)=STATEV(I)
      END DO
      DREF(1)=D1
      DREF(2)=D2
      DREF(3)=D3
      DREF(4)=D4
      DREF(5)=0.D0
      DREF(6)=0.D0
C     Analytic tangent at the reference increment.
      DO I=1,6
        STRESS(I)=SR0(I)
        DSTRAN(I)=DREF(I)
      END DO
      DO I=1,14
        STATEV(I)=ST0(I)
      END DO
      CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,14,31,PNEWDT)
      DO I=1,6
        DO J=1,6
          CANA(I,J)=DDSDDE(I,J)
        END DO
      END DO
C     Central FD about the reference increment, from the same state n.
      H=1.0D-9
      DO J=1,6
        DO I=1,6
          STRESS(I)=SR0(I)
          DSTRAN(I)=DREF(I)
        END DO
        DSTRAN(J)=DREF(J)+H
        DO I=1,14
          STATEV(I)=ST0(I)
        END DO
        CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,14,31,
     1             PNEWDT)
        DO I=1,6
          SP(I)=STRESS(I)
        END DO
        DO I=1,6
          STRESS(I)=SR0(I)
          DSTRAN(I)=DREF(I)
        END DO
        DSTRAN(J)=DREF(J)-H
        DO I=1,14
          STATEV(I)=ST0(I)
        END DO
        CALL CALLU(CMNAME,STRESS,STATEV,DDSDDE,STRAN,DSTRAN,P,14,31,
     1             PNEWDT)
        DO I=1,6
          SM(I)=STRESS(I)
        END DO
        DO I=1,6
          CNUM(I,J)=(SP(I)-SM(I))/(2.0D0*H)
        END DO
      END DO
      ERRMAX=0.D0
      SCAL=1.D0
      DO I=1,6
        DO J=1,6
          IF (ABS(CANA(I,J)).GT.SCAL) SCAL=ABS(CANA(I,J))
          D=ABS(CNUM(I,J)-CANA(I,J))
          IF (D.GT.ERRMAX) ERRMAX=D
        END DO
      END DO
      RELERR=100.D0*ERRMAX/SCAL
      RETURN
      END
C-----------------------------------------------------------------------
      SUBROUTINE SAVEST(SV,N)
      IMPLICIT REAL*8(A-H,O-Z)
      DIMENSION SV(N),SAV(30)
      COMMON /CSAV/ SAV
      DO I=1,N
        SAV(I)=SV(I)
      END DO
      RETURN
      END
      SUBROUTINE RESTST(SV,N)
      IMPLICIT REAL*8(A-H,O-Z)
      DIMENSION SV(N),SAV(30)
      COMMON /CSAV/ SAV
      DO I=1,N
        SV(I)=SAV(I)
      END DO
      RETURN
      END
