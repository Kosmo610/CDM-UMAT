C=======================================================================
C  kmacro_driver.f
C
C  Stand-alone driver that calls the REAL KMACRO31 / KYARN31 / KMTRX31
C  subroutines of src/UMAT_CSIC_THERMSHOCK_V3_0.for at a single material
C  point, so the Fortran that Abaqus will actually execute can be checked
C  against the Python mirror in verify_thermshock.py.
C
C  Without this, "the model is verified" would only mean "the Python
C  re-implementation is verified" -- the two could disagree and no test
C  here would notice.  Compiled and driven by cross_check_fortran.py.
C
C  Build (see cross_check_fortran.py, which does it automatically):
C    gfortran -ffixed-form -std=legacy -o kmacro_driver \
C             kmacro_driver.f umat_stub_wrapped.f
C
C  Input on stdin, free format:
C    KIND                     1 = macro, 2 = yarn, 3 = matrix
C    NPROPS
C    PROPS(1..NPROPS)
C    NSTATV
C    STATEV(1..NSTATV)
C    EPS(1..6)
C    TEMP DTEMP DTIME FLDV CELENT KSTEP
C  Output on stdout:
C    line 1  : STRESS(1..6)
C    line 2  : STATEV(1..NSTATV)
C    line 3  : DDSDDE diagonal (1..6)
C    line 4  : PNEWDT
C=======================================================================
      PROGRAM KMACRO_DRIVER
      IMPLICIT NONE
      INTEGER MAXP,MAXS
      PARAMETER (MAXP=400,MAXS=40)
      DOUBLE PRECISION P(MAXP),SV(MAXS),EPS(6),STRESS(6),CTAN(6,6)
      DOUBLE PRECISION TEMP,DTEMP,DTIME,FLDV,CELENT,PNEWDT
      INTEGER KIND,NPROPS,NSTATV,KSTEP,I,J,NT
C
      READ(*,*) KIND
      READ(*,*) NPROPS
      IF (NPROPS.GT.MAXP) STOP 'NPROPS too large'
      READ(*,*) (P(I),I=1,NPROPS)
      READ(*,*) NSTATV
      IF (NSTATV.GT.MAXS) STOP 'NSTATV too large'
      READ(*,*) (SV(I),I=1,NSTATV)
      READ(*,*) (EPS(I),I=1,6)
      READ(*,*) TEMP,DTEMP,DTIME,FLDV,CELENT,KSTEP
C
      DO I=1,6
         STRESS(I)=0.0D0
         DO J=1,6
            CTAN(I,J)=0.0D0
         END DO
      END DO
      PNEWDT=1.0D0
C
      IF (KIND.EQ.1) THEN
         NT=NINT(P(47))
         CALL KMACRO31(EPS,STRESS,CTAN,SV,P,NT,DTIME,TEMP,DTEMP,
     1        FLDV,PNEWDT,KSTEP,CELENT)
      ELSE IF (KIND.EQ.2) THEN
         IF (NPROPS.EQ.38) THEN
            NT=0
         ELSE
            NT=NINT(P(40))
         END IF
         CALL KYARN31(EPS,STRESS,CTAN,SV,P,NPROPS,NT,DTIME,
     1        TEMP,DTEMP,PNEWDT,KSTEP,CELENT,NSTATV)
      ELSE
         IF (NPROPS.EQ.22) THEN
            NT=0
         ELSE
            NT=NINT(P(23))
         END IF
         CALL KMTRX31(EPS,STRESS,CTAN,SV,P,NT,DTIME,TEMP,DTEMP,
     1        PNEWDT,KSTEP,CELENT)
      END IF
C
      WRITE(*,'(6(1PE24.16,1X))') (STRESS(I),I=1,6)
      WRITE(*,'(40(1PE24.16,1X))') (SV(I),I=1,NSTATV)
      WRITE(*,'(6(1PE24.16,1X))') (CTAN(I,I),I=1,6)
      WRITE(*,'(1PE24.16)') PNEWDT
      END
C=======================================================================
      SUBROUTINE XIT
C     Abaqus supplies XIT at run time; this is the stand-alone stand-in.
      WRITE(*,*) 'XIT called -- aborting'
      STOP 1
      END
