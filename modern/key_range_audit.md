# Key / Range Audit -- OpenHymnal Lead Sheets

## Summary

- Total hymns: 287
- Pipeline-ready (pass all 5 checks): 261
- Exceptions: 26

287 hymns audited: 261 pipeline-ready, 26 exceptions.

## Key distribution

| key | count |
| :-- | ----: |
| Eb | 29 |
| Bb | 20 |
| F | 59 |
| C | 42 |
| G | 81 |
| D | 41 |
| A | 9 |
| E | 6 |

## Range distribution

- Global min MIDI: 58 (A#3)
- Global max MIDI: 78 (F#5)
- Harp range (enforced): 36 (C2) .. 91 (G6)

## Meter distribution

| meter | count |
| :-- | ----: |
| 4/4 | 192 |
| 3/4 | 45 |
| none (EXOTIC) | 17 |
| 6/4 | 10 |
| 3/2 (EXOTIC) | 7 |
| 2/4 | 5 |
| 6/8 | 5 |
| 2/2 | 3 |
| 8/4 (EXOTIC) | 2 |
| 9/8 | 1 |

## Chord annotation counts

| bucket | hymns |
| :-- | ----: |
| 0 | 0 |
| 1-4 | 0 |
| 5-9 | 1 |
| 10-19 | 16 |
| 20-39 | 155 |
| 40-79 | 109 |
| 80+ | 6 |

## Tempo distribution (quarter-note BPM)

- Hymns with parseable tempo: 287 / 287
- Min: 60.0
- Median: 120.0
- Max: 230.0

## Exception lists

### Key not in lever-harp set (0)

_(none)_

### Exotic meter (26)

| n | title | key | meter | anns | tempo | failures |
| :-- | :-- | :-- | :-- | ---: | ---: | :-- |
| 4041 | Of The Father's Love Begotten | F | none | 43 | 120 | meter='none' not simple |
| 4046 | A Great and Mighty Wonder | F | none | 31 | 100 | meter='none' not simple |
| 4063 | Lo, How A Rose E'er Blooming | F | none | 31 | 100 | meter='none' not simple |
| 4102 | Were You There? | E | none | 36 | 100 | meter='none' not simple |
| 4114 | The Cloud Received Christ From Their Sig | G | 3/2 | 15 | 200 | meter='3/2' not simple |
| 4120 | Holy Spirit, Ever Dwelling | G | 8/4 | 52 | 180 | meter='8/4' not simple |
| 4122 | God the Father Be Our Stay | D | none | 80 | 100 | meter='none' not simple |
| 4126 | We All Believe in One True God | C | none | 91 | 120 | meter='none' not simple |
| 4133 | Lord, Keep Us Steadfast in Thy Word | G | none | 29 | 150 | meter='none' not simple |
| 4139 | Have Mercy On Me, O My God | Bb | none | 37 | 100 | meter='none' not simple |
| 4140 | Jesus Sinners Doth Receive | G | none | 36 | 120 | meter='none' not simple |
| 4173 | None Other Lamb | D | 3/2 | 26 | 110 | meter='3/2' not simple |
| 4174 | O Be Glad All Nations on Earth | F | 3/2 | 61 | 230 | meter='3/2' not simple |
| 4175 | O For A Thousand Tongues | G | 3/2 | 15 | 200 | meter='3/2' not simple |
| 4176 | O The Deep, Deep Love of Jesus | G | 8/4 | 52 | 180 | meter='8/4' not simple |
| 4182 | By Grace I'm Saved | F | none | 37 | 120 | meter='none' not simple |
| 4203 | Christ Returneth | D | none | 51 | 120 | meter='none' not simple |
| 4209 | Wake, Awake, for Night Is Flying | C | none | 35 | 160 | meter='none' not simple |
| 4231 | O That The Lord Would Guide My Ways | G | 3/2 | 19 | 130 | meter='3/2' not simple |
| 4258 | Praise God From Whom All Blessings Flow | G | none | 26 | 120 | meter='none' not simple |
| 4269 | Now Thank We All Our God | F | none | 37 | 120 | meter='none' not simple |
| 4285 | The Lord's My Shepherd | D | 3/2 | 39 | 100 | meter='3/2' not simple |
| 4303 | Savior, Who Thy Flock Art Feeding | F | none | 29 | 130 | meter='none' not simple |
| 4304 | You Parents Hear What Jesus Taught | F | 3/2 | 27 | 125 | meter='3/2' not simple |
| 4306 | Awake, My Soul, And With The Sun | G | none | 26 | 120 | meter='none' not simple |
| 4314 | O Trinity of Blessed Light | D | none | 26 | 60 | meter='none' not simple |

### Zero chord annotations (0)

_(none)_

### Missing/unparseable tempo (0)

_(none)_

### Notes out of harp range (0)

_(none)_

### All exceptions (combined)

| n | title | failures |
| :-- | :-- | :-- |
| 4041 | Of The Father's Love Begotten | meter='none' not simple |
| 4046 | A Great and Mighty Wonder | meter='none' not simple |
| 4063 | Lo, How A Rose E'er Blooming | meter='none' not simple |
| 4102 | Were You There? | meter='none' not simple |
| 4114 | The Cloud Received Christ From Their Sig | meter='3/2' not simple |
| 4120 | Holy Spirit, Ever Dwelling | meter='8/4' not simple |
| 4122 | God the Father Be Our Stay | meter='none' not simple |
| 4126 | We All Believe in One True God | meter='none' not simple |
| 4133 | Lord, Keep Us Steadfast in Thy Word | meter='none' not simple |
| 4139 | Have Mercy On Me, O My God | meter='none' not simple |
| 4140 | Jesus Sinners Doth Receive | meter='none' not simple |
| 4173 | None Other Lamb | meter='3/2' not simple |
| 4174 | O Be Glad All Nations on Earth | meter='3/2' not simple |
| 4175 | O For A Thousand Tongues | meter='3/2' not simple |
| 4176 | O The Deep, Deep Love of Jesus | meter='8/4' not simple |
| 4182 | By Grace I'm Saved | meter='none' not simple |
| 4203 | Christ Returneth | meter='none' not simple |
| 4209 | Wake, Awake, for Night Is Flying | meter='none' not simple |
| 4231 | O That The Lord Would Guide My Ways | meter='3/2' not simple |
| 4258 | Praise God From Whom All Blessings Flow | meter='none' not simple |
| 4269 | Now Thank We All Our God | meter='none' not simple |
| 4285 | The Lord's My Shepherd | meter='3/2' not simple |
| 4303 | Savior, Who Thy Flock Art Feeding | meter='none' not simple |
| 4304 | You Parents Hear What Jesus Taught | meter='3/2' not simple |
| 4306 | Awake, My Soul, And With The Sun | meter='none' not simple |
| 4314 | O Trinity of Blessed Light | meter='none' not simple |
