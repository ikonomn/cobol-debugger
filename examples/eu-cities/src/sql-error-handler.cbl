      ******************************************************************
      * Common callable SQL error reporter for GixSQL applications.
      * DB-FLAG: 00=SQLite, 01=MariaDB.
      * ACTION:  R=retryable, D=duplicate, F=fatal, E=other error.
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SQL-ERROR-HANDLER.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-ABS-CODE PIC 9(9) COMP-5 VALUE ZERO.

       LINKAGE SECTION.
       01 LK-DB-FLAG      PIC X(2).
       01 LK-SQLCODE      PIC S9(9) COMP-5.
       01 LK-SQLSTATE     PIC X(5).
       01 LK-CURRENT-STEP PIC X(24).
       01 LK-SQLERRMC     PIC X(70).
       01 LK-SQLERRML     PIC S9(4) COMP-5.
       01 LK-ACTION       PIC X.

       PROCEDURE DIVISION USING
           LK-DB-FLAG
           LK-SQLCODE
           LK-SQLSTATE
           LK-CURRENT-STEP
           LK-SQLERRMC
           LK-SQLERRML
           LK-ACTION.

       MAIN-PROCEDURE.
           MOVE "E" TO LK-ACTION
           COMPUTE WS-ABS-CODE = FUNCTION ABS(LK-SQLCODE)

           DISPLAY FUNCTION TRIM(LK-CURRENT-STEP)
               " SQLCODE=" LK-SQLCODE
               " SQLSTATE=" LK-SQLSTATE
           IF LK-SQLERRML > ZERO
               IF LK-SQLERRML > 70
                   DISPLAY LK-SQLERRMC
               ELSE
                   DISPLAY LK-SQLERRMC(1:LK-SQLERRML)
               END-IF
           END-IF

           EVALUATE LK-DB-FLAG
               WHEN "00"
                   PERFORM HANDLE-SQLITE-ERROR
               WHEN "01"
                   PERFORM HANDLE-MARIADB-ERROR
               WHEN OTHER
                   DISPLAY "UNKNOWN DB-FLAG: " LK-DB-FLAG
                   MOVE "F" TO LK-ACTION
           END-EVALUATE
           GOBACK.

       HANDLE-SQLITE-ERROR.
           EVALUATE TRUE
               WHEN WS-ABS-CODE = 5
               WHEN WS-ABS-CODE = 6
               WHEN LK-SQLSTATE = "40001"
                   DISPLAY "SQLITE RETRYABLE: DATABASE IS LOCKED"
                   MOVE "R" TO LK-ACTION
               WHEN WS-ABS-CODE = 19
               WHEN LK-SQLSTATE(1:2) = "23"
                   DISPLAY "SQLITE CONSTRAINT VIOLATION"
               WHEN WS-ABS-CODE = 7
               WHEN WS-ABS-CODE = 10
               WHEN WS-ABS-CODE = 13
                   DISPLAY "SQLITE CRITICAL SYSTEM OR STORAGE ERROR"
                   MOVE "F" TO LK-ACTION
               WHEN WS-ABS-CODE = 11
               WHEN WS-ABS-CODE = 26
                   DISPLAY "SQLITE DATABASE FILE MAY BE CORRUPT"
                   MOVE "F" TO LK-ACTION
               WHEN OTHER
                   DISPLAY "SQLITE ERROR"
           END-EVALUATE.

       HANDLE-MARIADB-ERROR.
           EVALUATE TRUE
               WHEN WS-ABS-CODE = 1021
                   DISPLAY "MARIADB CRITICAL: OUT OF DISK SPACE"
                   MOVE "F" TO LK-ACTION
               WHEN WS-ABS-CODE = 1037
               WHEN WS-ABS-CODE = 1038
                   DISPLAY "MARIADB CRITICAL: OUT OF MEMORY"
                   MOVE "F" TO LK-ACTION
               WHEN WS-ABS-CODE = 1022
               WHEN WS-ABS-CODE = 1062
               WHEN LK-SQLSTATE = "23000"
                   DISPLAY "MARIADB DUPLICATE OR CONSTRAINT ERROR"
                   MOVE "D" TO LK-ACTION
               WHEN WS-ABS-CODE = 1051
               WHEN LK-SQLSTATE = "42S02"
                   DISPLAY "MARIADB TABLE DOES NOT EXIST"
                   MOVE "F" TO LK-ACTION
               WHEN WS-ABS-CODE = 1054
               WHEN LK-SQLSTATE = "42S22"
                   DISPLAY "MARIADB COLUMN DOES NOT EXIST"
                   MOVE "F" TO LK-ACTION
               WHEN WS-ABS-CODE = 1205
               WHEN WS-ABS-CODE = 1213
               WHEN LK-SQLSTATE = "40001"
                   DISPLAY "MARIADB RETRYABLE LOCK ERROR"
                   MOVE "R" TO LK-ACTION
               WHEN LK-SQLSTATE(1:2) = "08"
                   DISPLAY "MARIADB CONNECTION ERROR"
                   MOVE "F" TO LK-ACTION
               WHEN OTHER
                   DISPLAY "MARIADB ERROR"
           END-EVALUATE.

       END PROGRAM SQL-ERROR-HANDLER.
