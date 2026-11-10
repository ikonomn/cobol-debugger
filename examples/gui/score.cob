       >>SOURCE FORMAT FREE
identification division.
program-id. score.
data division.
working-storage section.
01 score pic 9 value 5.
01 selection pic 9.
procedure division.
    call static "choose_score" returning selection
    if selection = 1
        add 1 to score
    else
        subtract 1 from score
    end-if
    display "SCORE: " score
    goback.
