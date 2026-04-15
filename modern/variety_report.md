# Modern Pipeline -- Voicing Variety Report

## Summary

- Hymns in lead_sheets.json: 287
- Hymns processed: 287
- Hymns skipped: 0
- Unparseable chord annotations (total): 263
- Total chord events reharmonized: 11568
- Voicing catalog size: 74
- Distinct voicings used: 58 (78.4% of catalog)
- Never-used voicings: 13
- Avg distinct RH chords per hymn: 9.84
- Avg distinct LH chords per hymn: 8.86
- Worst-case diversity: hymn 4215 (Behold, A Host, Arrayed in White) -- 15 distinct voicings / 70 events = 0.21
- Best-case diversity:  hymn 4038 (Magnificat) -- 21 distinct voicings / 23 events = 0.91

### Interpretation

Catalog coverage is good (78%).

## Top 10 Voicings by Usage

| rank | RH | LH | count | %% of events | description |
| ---: | :--- | :--- | ---: | ---: | :--- |
| 1 | V | vi7 | 1549 | 13.4% | vim13 |
| 2 | IV | viio | 1080 | 9.3% | viio11 |
| 3 | iii | vi | 692 | 6.0% | vim7+9 |
| 4 | vi | I | 681 | 5.9% | Pastoral I6 |
| 5 | I | ii7 | 543 | 4.7% | iim11 - Dm11 voicing |
| 6 | Vsus4 | V | 491 | 4.2% | Quartal V |
| 7 | Isus4 | I | 476 | 4.1% | Sus4 hang |
| 8 | V | ii | 375 | 3.2% | iim7+11 |
| 9 | I | V7 | 335 | 2.9% | V13 |
| 10 | Imaj7 | V7 | 315 | 2.7% | Cadence approach |

## Bottom 10 Voicings (least used, zeros included)

| rank | RH | LH | count | description |
| ---: | :--- | :--- | ---: | :--- |
| 1 | I | Imaj7 | 0 | Doubled tonic |
| 2 | ii | Imaj7 | 0 | Full jazz tonic |
| 3 | ii | IVmaj7 | 0 | IV?9+6 |
| 4 | iii | Imaj7 | 0 | Sparse I?9 |
| 5 | iii | IVmaj7 | 0 | IV?911 alt |
| 6 | IV | Imaj7 | 0 | Lydian tonic |
| 7 | V | I | 0 | Bright I6/9 |
| 8 | V | Imaj7 | 0 | Gospel tonic |
| 9 | V | IVmaj7 | 0 | Full Lydian |
| 10 | V7 | Imaj7 | 0 | Prep. cadence |

## Usage Histogram

V/vi7               1549 ########################################
IV/viio             1080 ############################
iii/vi               692 ##################
vi/I                 681 ##################
I/ii7                543 ##############
Vsus4/V              491 #############
Isus4/I              476 ############
V/ii                 375 ##########
I/V7                 335 #########
Imaj7/V7             315 ########
ii/I                 302 ########
iii/ii               281 #######
V/ii7                280 #######
I/vi                 247 ######
V/iii                235 ######
I/ii                 227 ######
I/V                  221 ######
iii/I                187 #####
iii/IV               161 ####
I/IV                 148 ####
vi/vi                142 ####
iii/V                139 ####
IVsus2/IV            139 ####
Vsus2/V              139 ####
IV/V                 138 ####
viio/vi              136 ####
iii/iii              129 ###
I/iii                119 ###
ii/ii                106 ###
IVmaj7/V7             98 ###
IV/I                  97 ###
V/vi                  90 ##
ii7/V7                88 ##
IV/ii                 84 ##
IV/vi                 82 ##
vi/ii                 80 ##
ii/V                  77 ##
vi/V7                 75 ##
IV/V7                 71 ##
vii/vii               67 ##
I/I                   66 ##
vi/iii                57 #
ii/vi                 48 #
Imaj7/IV              47 #
IV/iii                44 #
IV/IV                 44 #
viio/iii              44 #
V/V                   43 #
vi/V                  43 #
V/V7                  41 #
vi/IV                 39 #
Isus2/I               33 #
ii/V7                 29 #
ii/iii7               22 #
ii/IV                 13 
viio/V                13 
Imaj7/I               10 
V/IV                  10 
I/Imaj7                0 
ii/Imaj7               0 
ii/IVmaj7              0 
iii/Imaj7              0 
iii/IVmaj7             0 
IV/Imaj7               0 
V/I                    0 
V/Imaj7                0 
V/IVmaj7               0 
V7/Imaj7               0 
vi/viio7(b5)           0 
viio/I                 0 
viio/Imaj7             0 

## Full Usage Table

| RH | LH | count | lh_fig | rh_fig | description |
| :--- | :--- | ---: | :--- | :--- | :--- |
| V | vi7 | 1549 | 6333 | C33 | vim13 |
| IV | viio | 1080 | 733 | B33 | viio11 |
| iii | vi | 692 | 633 | A33 | vim7+9 |
| vi | I | 681 | 133 | 633 | Pastoral I6 |
| I | ii7 | 543 | 2333 | 833 | iim11 - Dm11 voicing |
| Vsus4 | V | 491 | 533 | C44 | Quartal V |
| Isus4 | I | 476 | 133 | 842 | Sus4 hang |
| V | ii | 375 | 233 | C33 | iim7+11 |
| I | V7 | 335 | 5333 | F33 | V13 |
| Imaj7 | V7 | 315 | 5333 | F333 | Cadence approach |
| ii | I | 302 | 133 | 933 | Warm I?9 |
| iii | ii | 281 | 233 | A33 | Mournful |
| V | ii7 | 280 | 2333 | C33 | Sec. dom of ii |
| I | vi | 247 | 633 | F33 | vim7 pad |
| V | iii | 235 | 333 | C33 | Phrygian tint |
| I | ii | 227 | 233 | 833 | iim7 |
| I | V | 221 | 533 | F33 | Vs4 hang |
| iii | I | 187 | 133 | A33 | Soft I? |
| iii | IV | 161 | 433 | A33 | IV?9 (alt) |
| I | IV | 148 | 433 | 833 | IV?9 |
| vi | vi | 142 | 633 | D334 | Rel.-minor bell |
| iii | V | 139 | 533 | A33 | V add 6 |
| IVsus2 | IV | 139 | 433 | B24 | Sus2 IV |
| Vsus2 | V | 139 | 533 | C24 | Sus2 V |
| IV | V | 138 | 533 | B33 | V11 modal |
| viio | vi | 136 | 633 | E33 | vim(maj7) |
| iii | iii | 129 | 333 | A334 | Mediant bell |
| I | iii | 119 | 333 | 833 | Mellow mediant |
| ii | ii | 106 | 233 | 9334 | Minor bell |
| IVmaj7 | V7 | 98 | 5333 | B333 | Jazzy pre-cadence |
| IV | I | 97 | 133 | B33 | Mixolydian blur |
| V | vi | 90 | 633 | C33 | Aeolian modal |
| ii7 | V7 | 88 | 5333 | G333 | Jazz ii--V |
| IV | ii | 84 | 233 | B33 | iim7+9 |
| IV | vi | 82 | 633 | B33 | vim6 |
| vi | ii | 80 | 233 | 633 | Rich |
| ii | V | 77 | 533 | 933 | V7+9 |
| vi | V7 | 75 | 5333 | D33 | V13 alt |
| IV | V7 | 71 | 5333 | B33 | V11 suspended |
| vii | vii | 67 | 733 | E334 | Leading-tone bell |
| I | I | 66 | 133 | 8334 | Bell-ring I |
| vi | iii | 57 | 333 | D33 | Phrygian add |
| ii | vi | 48 | 633 | G33 | Spacious minor |
| Imaj7 | IV | 47 | 433 | 8333 | Double- |
| IV | iii | 44 | 333 | B33 | Dark Phrygian |
| IV | IV | 44 | 433 | B334 | Subdominant bell |
| viio | iii | 44 | 333 | 733 | iiim75 |
| V | V | 43 | 533 | C334 | Dominant bell |
| vi | V | 43 | 533 | D33 | Warm V7+9 |
| V | V7 | 41 | 5333 | C33 | V7 thick |
| vi | IV | 39 | 433 | D33 | IV? warm |
| Isus2 | I | 33 | 133 | 824 | Sus2 open |
| ii | V7 | 29 | 5333 | G33 | Jazz V79 |
| ii | iii7 | 22 | 3333 | 933 | iiim11 |
| ii | IV | 13 | 433 | 933 | IV add 6/9 |
| viio | V | 13 | 533 | E33 | V7 bite |
| Imaj7 | I | 10 | 133 | 8333 | Full maj7 stack |
| V | IV | 10 | 433 | C33 | Lydian |
| I | Imaj7 | 0 | 1333 | 833 | Doubled tonic |
| ii | Imaj7 | 0 | 1333 | 933 | Full jazz tonic |
| ii | IVmaj7 | 0 | 4333 | G33 | IV?9+6 |
| iii | Imaj7 | 0 | 1333 | A33 | Sparse I?9 |
| iii | IVmaj7 | 0 | 4333 | A33 | IV?911 alt |
| IV | Imaj7 | 0 | 1333 | B33 | Lydian tonic |
| V | I | 0 | 133 | 533 | Bright I6/9 |
| V | Imaj7 | 0 | 1333 | C33 | Gospel tonic |
| V | IVmaj7 | 0 | 4333 | C33 | Full Lydian |
| V7 | Imaj7 | 0 | 1333 | C333 | Prep. cadence |
| vi | viio7(b5) | 0 | 7333 | D33 | viio13 |
| viio | I | 0 | 133 | 733 | Tense I? |
| viio | Imaj7 | 0 | 1333 | 733 | I?911 |

## Never-Used Voicings

| RH | LH | lh_fig | rh_fig | description |
| :--- | :--- | :--- | :--- | :--- |
| I | Imaj7 | 1333 | 833 | Doubled tonic |
| ii | Imaj7 | 1333 | 933 | Full jazz tonic |
| ii | IVmaj7 | 4333 | G33 | IV?9+6 |
| iii | Imaj7 | 1333 | A33 | Sparse I?9 |
| iii | IVmaj7 | 4333 | A33 | IV?911 alt |
| IV | Imaj7 | 1333 | B33 | Lydian tonic |
| V | I | 133 | 533 | Bright I6/9 |
| V | Imaj7 | 1333 | C33 | Gospel tonic |
| V | IVmaj7 | 4333 | C33 | Full Lydian |
| V7 | Imaj7 | 1333 | C333 | Prep. cadence |
| vi | viio7(b5) | 7333 | D33 | viio13 |
| viio | I | 133 | 733 | Tense I? |
| viio | Imaj7 | 1333 | 733 | I?911 |

## Overused Voicings (>= 20%% of events)

_(none -- no single voicing accounts for >= 20%% of events)_

## Low-Diversity Example Hymns (developer eyeballing)

| hymn | key | events | distinct voicings | distinct RH | distinct LH | ratio | title |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 4215 | Eb | 70 | 15 | 7 | 9 | 0.21 | Behold, A Host, Arrayed in White |
| 4125 | Eb | 163 | 38 | 11 | 10 | 0.23 | Isaiah, Mighty Seer, In Days of Old |
| 4180 | F | 53 | 13 | 7 | 8 | 0.25 | The Lily of the Valley |
