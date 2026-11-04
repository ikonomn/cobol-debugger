       identification division.
       program-id. hello.
       data division.
       working-storage section.
       01 counter pic 9 value 1.
       procedure division.
           add 1 to counter
           display "Counter: " counter
           stop run.
