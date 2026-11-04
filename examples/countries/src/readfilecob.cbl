      ******************************************************************
      * AUTHOR:
      * DATE:
      * PURPOSE:
      * TECTONICS:cobc -x -Xref -ftsymbols -Treadfilecob.lst readfilecob.cbl 
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COUNTRIES.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER.  GNUCOBOL.
       OBJECT-COMPUTER.  GNUCOBOL.
       SPECIAL-NAMES.
            DECIMAL-POINT IS COMMA.
       REPOSITORY.
           FUNCTION ALL INTRINSIC.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT COUNTRIES-FILE ASSIGN TO DISK "countries.txt"
           ORGANIZATION IS LINE SEQUENTIAL
           ACCESS MODE IS SEQUENTIAL
           FILE STATUS IS COUNTRIES-STATUS.

       DATA DIVISION.
       FILE SECTION.

       FD COUNTRIES-FILE
          LABEL RECORD OMITTED
          DATA RECORD IS COUNTRIES-REC.

       01 COUNTRIES-REC.
          05 COUNTRIES-ISO2     PIC X(2).
          05 FILLER             PIC X.
          05 COUNTRIES-NAME     PIC X(47).


       WORKING-STORAGE SECTION.
      
      *01 W-MAX-LENGTH PIC 9(09) VALUE ZERO.
       
       01 COUNTRIES-STATUS                PIC X(2).

 
       01 W-LINE.
          05 FILLER        PIC X(05) VALUE 'line '.
          05 FILLER        PIC X     VALUE '['.
          05 COUNTRY-TOTAL PIC 9(06) VALUE ZERO.
          05 FILLER        PIC X(02) VALUE ']:'.
          05 COUNTRY-LINE  PIC X(50) VALUE SPACES.
          
      * 01 W-TOTAL-RECS.
      *    05 FILLER  PIC    X(26) VALUE "Records in countries.txt :".
      *    05 COUNTRY-TOTAL PIC 9(09)  VALUE ZERO.


       PROCEDURE DIVISION.


       MAIN-PROCEDURE.

           PERFORM  OPEN-FILES THRU OPEN-FILES-EXIT
           PERFORM  READ-COUNTRIES-FILE THRU
                    READ-COUNTRIES-FILE-EXIT
           UNTIL
           COUNTRIES-STATUS = 10.

      *    DISPLAY W-TOTAL-RECS
      *    DISPLAY W-MAX-LENGTH
           PERFORM CLOSE-FILES THRU CLOSE-FILES-EXIT
           STOP RUN.

       READ-COUNTRIES-FILE.
           READ COUNTRIES-FILE NEXT RECORD INTO COUNTRY-LINE
                AT END
                    CONTINUE
                NOT AT END
                
      *         IF LENGTH(TRIM(COUNTRIES-REC)) > W-MAX-LENGTH
      *              MOVE LENGTH(TRIM(COUNTRIES-REC)) TO W-MAX-LENGTH
      *         END-IF
                   
                ADD 1 TO COUNTRY-TOTAL
                DISPLAY W-LINE
           END-READ.

       READ-COUNTRIES-FILE-EXIT. EXIT.

       OPEN-FILES.
            OPEN INPUT COUNTRIES-FILE.
       OPEN-FILES-EXIT. EXIT.

       CLOSE-FILES.
            CLOSE COUNTRIES-FILE.
       CLOSE-FILES-EXIT. EXIT.

       END PROGRAM COUNTRIES.
       
      *cobc.exe -x -o bin\%e -std=default -w -wall -debug -xref -ftsymbols -T%e.lst %f.cbl
      
      *cobc -x -Xref -ftsymbols -T%e.lst %f


