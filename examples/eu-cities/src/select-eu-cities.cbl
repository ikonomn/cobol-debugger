      ******************************************************************
      * Display every city whose ISO2 country code is GR.
      * Runtime settings are read from DB_CONFIG_FILE.
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SELECT-EU-CITIES.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           COPY "db-config-select.cpy".

       DATA DIVISION.
       FILE SECTION.
       COPY "db-config-fd.cpy".

       WORKING-STORAGE SECTION.
       EXEC SQL INCLUDE DB-CONFIG-WS END-EXEC.
       01 ROW-COUNT         PIC 9(9) VALUE ZERO.

       01 CITY-ROW.
          05 CITY-ID        PIC X(15).
          05 CITY-NAME      PIC X(60).
          05 CITY-ASCII     PIC X(60).
          05 CITY-LATITUDE  PIC X(12).
          05 CITY-LONGITUDE PIC X(12).
          05 COUNTRY-NAME   PIC X(60).
          05 CITY-ISO2      PIC X(2).
          05 CITY-ISO3      PIC X(3).
          05 ADMIN-NAME     PIC X(60).
          05 CAPITAL        PIC X(7).
          05 POPULATION     PIC X(15).

       EXEC SQL INCLUDE SQLCA END-EXEC.


       EXEC SQL
           DECLARE GRC CURSOR FOR
            SELECT *
            FROM cities_new INDEXED BY cities_new_iso2_city_idx
            ORDER BY iso2, city;
       END-EXEC.

       PROCEDURE DIVISION.
       MAIN-PROCEDURE.
           MOVE "00" TO DB-FLAG
           PERFORM LOAD-DB-CONFIG
           IF NOT DB-CONFIG-OK
               MOVE 2 TO RETURN-CODE
               STOP RUN
           END-IF
           IF DATASRC = SPACES
               DISPLAY "DATASRC is required"
               MOVE 2 TO RETURN-CODE
               STOP RUN
           END-IF

           MOVE "CONNECT" TO CURRENT-STEP
           EXEC SQL
               CONNECT :DB-USER IDENTIFIED BY :DB-PASSWORD
                   USING :DATASRC
           END-EXEC
           IF SQLCODE NOT = ZERO
               PERFORM REPORT-SQL-ERROR
               STOP RUN
           END-IF

           MOVE "OPEN CURSOR" TO CURRENT-STEP
           EXEC SQL OPEN GRC END-EXEC
           IF SQLCODE NOT = ZERO
               PERFORM REPORT-SQL-ERROR
               EXEC SQL CONNECT RESET END-EXEC
               STOP RUN
           END-IF

           PERFORM FETCH-EU-CITY
           PERFORM UNTIL SQLCODE = 100 OR SQLCODE < ZERO
               ADD 1 TO ROW-COUNT
               PERFORM DISPLAY-CITY
               PERFORM FETCH-EU-CITY
           END-PERFORM

           IF SQLCODE < ZERO
               PERFORM REPORT-SQL-ERROR
           END-IF
           EXEC SQL CLOSE GRC END-EXEC
           EXEC SQL CONNECT RESET END-EXEC
           DISPLAY "EU CITIES: " ROW-COUNT
           STOP RUN.

       FETCH-EU-CITY.
           INITIALIZE CITY-ROW
           MOVE "FETCH CURSOR" TO CURRENT-STEP
           EXEC SQL
               FETCH GRC INTO
                   :CITY-ID, :CITY-NAME, :CITY-ASCII,
                   :CITY-LATITUDE, :CITY-LONGITUDE, :COUNTRY-NAME,
                   :CITY-ISO2, :CITY-ISO3, :ADMIN-NAME,
                   :CAPITAL, :POPULATION
           END-EXEC.

       DISPLAY-CITY.
           DISPLAY FUNCTION TRIM(CITY-NAME)
               " | " FUNCTION TRIM(COUNTRY-NAME)
               " | " FUNCTION TRIM(ADMIN-NAME)
               " | " FUNCTION TRIM(CAPITAL)
               " | population=" FUNCTION TRIM(POPULATION)
               " | id=" FUNCTION TRIM(CITY-ID).

       COPY "db-config-procedure.cpy".
