# Modern Pipeline -- Meter Exception Report

- hymns: 26
- pipeline-ready (preprocess + reharm + abc2ly): 25
- successfully rendered (LilyPond PDF): 25

Any hymn whose only failure is in stage 2 with an error containing a chord-name character (e.g. `#`, `b`, `o`, `?`) is tripping a pre-existing bug in the pipeline's unparseable-chord fallback, not in the meter handler. Stage 1 and stage 3 are the meter-handler contract; both pass for all 26.

Columns:

- **orig meter** / **eff meter**: meter before and after `meter_handler.preprocess_abc`.
- **meas**: measure count after preprocessing (for M:none splits, the number of 4/4 sub-measures; otherwise the source's own bar count).
- **anns pre/post**: chord annotation counts before and after preprocessing (must match).
- **s1..s4**: preprocess, pipeline, abc2ly, lilypond.

| n | title | key | orig meter | eff meter | meas | anns pre/post | s1 | s2 | s3 | s4 | notes |
| ---: | :--- | :-- | :-- | :-- | ---: | :-- | :-: | :-: | :-: | :-: | :-- |
| 4041 | Of The Father's Love Begotten | F | `none` | `4/4` | 20 | 43/43 | Y | Y | Y | Y |  |
| 4046 | A Great and Mighty Wonder | F | `none` | `4/4` | 18 | 31/31 | Y | Y | Y | Y |  |
| 4063 | Lo, How A Rose E'er Blooming | F | `none` | `4/4` | 18 | 31/31 | Y | Y | Y | Y |  |
| 4102 | Were You There? | E | `none` | `4/4` | 17 | 36/36 | Y | Y | Y | Y |  |
| 4114 | The Cloud Received Christ From Their Sig | G | `3/2` | `3/2` | 9 | 15/15 | Y | Y | Y | Y |  |
| 4120 | Holy Spirit, Ever Dwelling | G | `8/4` | `8/4` | 16 | 52/52 | Y | Y | Y | Y |  |
| 4122 | God the Father Be Our Stay | D | `none` | `4/4` | 29 | 80/80 | Y | Y | Y | Y |  |
| 4126 | We All Believe in One True God | C | `none` | `4/4` | 32 | 91/91 | Y | Y | Y | Y |  |
| 4133 | Lord, Keep Us Steadfast in Thy Word | G | `none` | `4/4` | 10 | 29/29 | Y | Y | Y | Y |  |
| 4139 | Have Mercy On Me, O My God | Bb | `none` | `4/4` | 20 | 37/37 | Y | Y | Y | Y |  |
| 4140 | Jesus Sinners Doth Receive | G | `none` | `4/4` | 13 | 36/36 | Y | N | Y | N | ValueError: label contains disallowed character '#' in 'C#' |
| 4173 | None Other Lamb | D | `3/2` | `3/2` | 9 | 26/26 | Y | Y | Y | Y |  |
| 4174 | O Be Glad All Nations on Earth | F | `3/2` | `3/2` | 32 | 61/61 | Y | Y | Y | Y |  |
| 4175 | O For A Thousand Tongues | G | `3/2` | `3/2` | 9 | 15/15 | Y | Y | Y | Y |  |
| 4176 | O The Deep, Deep Love of Jesus | G | `8/4` | `8/4` | 16 | 52/52 | Y | Y | Y | Y |  |
| 4182 | By Grace I'm Saved | F | `none` | `4/4` | 16 | 37/37 | Y | Y | Y | Y |  |
| 4203 | Christ Returneth | D | `none` | `4/4` | 21 | 51/51 | Y | Y | Y | Y |  |
| 4209 | Wake, Awake, for Night Is Flying | C | `none` | `4/4` | 32 | 35/35 | Y | Y | Y | Y |  |
| 4231 | O That The Lord Would Guide My Ways | G | `3/2` | `3/2` | 9 | 19/19 | Y | Y | Y | Y |  |
| 4258 | Praise God From Whom All Blessings Flow | G | `none` | `4/4` | 13 | 26/26 | Y | Y | Y | Y |  |
| 4269 | Now Thank We All Our God | F | `none` | `4/4` | 18 | 37/37 | Y | Y | Y | Y |  |
| 4285 | The Lord's My Shepherd | D | `3/2` | `3/2` | 17 | 39/39 | Y | Y | Y | Y |  |
| 4303 | Savior, Who Thy Flock Art Feeding | F | `none` | `4/4` | 10 | 29/29 | Y | Y | Y | Y |  |
| 4304 | You Parents Hear What Jesus Taught | F | `3/2` | `3/2` | 9 | 27/27 | Y | Y | Y | Y |  |
| 4306 | Awake, My Soul, And With The Sun | G | `none` | `4/4` | 13 | 26/26 | Y | Y | Y | Y |  |
| 4314 | O Trinity of Blessed Light | D | `none` | `4/4` | 8 | 26/26 | Y | Y | Y | Y |  |
