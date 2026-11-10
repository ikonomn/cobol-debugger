       LOAD-DB-CONFIG.
           MOVE "N" TO DB-CONFIG-OK-FLAG
           DISPLAY "DB_CONFIG_FILE" UPON ENVIRONMENT-NAME
           ACCEPT DB-CONFIG-PATH FROM ENVIRONMENT-VALUE
           IF DB-CONFIG-PATH = SPACES
               IF SQLITE
                   MOVE "../config/eu-cities-sqlite.conf"
                       TO DB-CONFIG-PATH
                   DISPLAY "DB_CONFIG_FILE not set; using SQLite"
               ELSE
                   IF MARIADB
                       MOVE "../config/worldcities-mariadb.conf"
                           TO DB-CONFIG-PATH
                       DISPLAY "DB_CONFIG_FILE not set; using MariaDB"
                   ELSE
                       DISPLAY "Invalid DB-FLAG: " DB-FLAG
                       EXIT PARAGRAPH
                   END-IF
               END-IF
           END-IF
           OPEN INPUT DB-CONFIG-FILE
           IF DB-CONFIG-STATUS NOT = "00"
               DISPLAY "Cannot open DB_CONFIG_FILE, status "
                   DB-CONFIG-STATUS
               EXIT PARAGRAPH
           END-IF
           DISPLAY "Using DB config: " FUNCTION TRIM(DB-CONFIG-PATH)
           PERFORM UNTIL DB-CONFIG-STATUS = "10"
               READ DB-CONFIG-FILE
                   AT END CONTINUE
                   NOT AT END PERFORM PARSE-DB-CONFIG-LINE
               END-READ
           END-PERFORM
           CLOSE DB-CONFIG-FILE
           IF DATASRC(1:7) = "sqlite:"
               MOVE "00" TO DB-FLAG
           ELSE
               IF DATASRC(1:6) = "mysql:"
                   MOVE "01" TO DB-FLAG
               END-IF
           END-IF
           DISPLAY "Using datasource: " FUNCTION TRIM(DATASRC)
           MOVE "Y" TO DB-CONFIG-OK-FLAG.

       PARSE-DB-CONFIG-LINE.
           EVALUATE TRUE
               WHEN DB-CONFIG-LINE(1:8) = "DATASRC="
                   MOVE DB-CONFIG-LINE(9:) TO DATASRC
               WHEN DB-CONFIG-LINE(1:12) = "DATASRC_USR="
                   MOVE DB-CONFIG-LINE(13:) TO DB-USER
               WHEN DB-CONFIG-LINE(1:12) = "DATASRC_PWD="
                   MOVE DB-CONFIG-LINE(13:) TO DB-PASSWORD
               WHEN DB-CONFIG-LINE(1:15) = "COUNTRIES_FILE="
                   MOVE DB-CONFIG-LINE(16:) TO COUNTRIES-PATH
               WHEN DB-CONFIG-LINE(1:12) = "CITIES_FILE="
                   MOVE DB-CONFIG-LINE(13:) TO CITIES-PATH
           END-EVALUATE.

       REPORT-SQL-ERROR.
           MOVE SPACE TO SQL-ERROR-ACTION
           CALL "SQL-ERROR-HANDLER" USING
               DB-FLAG
               SQLCODE
               SQLSTATE
               CURRENT-STEP
               SQLERRMC
               SQLERRML
               SQL-ERROR-ACTION
           END-CALL
           MOVE 1 TO RETURN-CODE.

       END-DB-CONFIG.
           EXIT.
