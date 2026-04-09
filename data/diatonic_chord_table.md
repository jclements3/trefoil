# Diatonic Harp Chord Table

## Core concept

A diatonic harp has 7 strings per octave. Chords are built by placing fingers on strings. The interval between fingers is expressed as a diatonic interval number (2=second, 3=third, 4=fourth, 5=fifth). No pinkies -- each hand uses 3 or 4 fingers maximum. Starting degree (1-7) + finger pattern = unique chord address.

## Pattern notation

Patterns are written as interval-interval (3-finger) or interval-interval-interval (4-finger). The starting degree is the column header. Each cell = degree + pattern = chord name.

## Chord symbol conventions

- Uppercase = major (I IV V)
- Lowercase = minor (iim iiim vim)
- deg = diminished (viideg)
- M7 = major 7th
- m7 = minor 7th
- 7 = dominant 7th
- o7 = half diminished 7th
- q = quartal
- s2 = sus2
- s4 = sus4
- 6 = major 6th
- m6 = minor 6th
- +9 = added 9th no 7th
- 9-3 = 9th chord omitting 3rd
- 9-5 = 9th chord omitting 5th
- Superscript at end = inversion (1 = 1st, 2 = 2nd, 3 = 3rd)
- -5 = omitted 5th
- Augmented = not available diatonically, requires lever changes

## The table

| Pattern | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---------|---|---|---|---|---|---|---|
| 2-4 | IM7-5^2 | iim7-5^2 | iiim7-5^2 | IVM7-5^2 | V7-5^2 | vim7-5^2 | Vq^2 |
| 3-3 | I | iim | iiim | IV | V | vim | viideg |
| 3-4 | I^1 | iim^1 | iiim^1 | IV^1 | V^1 | vim^1 | viideg^1 |
| 4-2 | IV^1 | V^1 | vi^1 | viideg^1 | I^1 | ii^1 | iiim^2 |
| 4-3 | I^2 | iim^2 | iiim^2 | IV^2 | V^2 | vim^2 | viideg^2 |
| 4-4 | Iq | iiq | iiiq | IVq | Vq | viq | viidegq |
| 2-3-3 | IM7^3 | iim7^3 | iiim7^3 | IVM7^3 | V7^3 | vim7^3 | viidego7^3 |
| 3-2-3 | IM7^2 | iim7^2 | iiim7^2 | IVM7^2 | V7^2 | vim7^2 | viidego7^2 |
| 3-3-2 | I6/iiim7^1 | iim6/IVM7^1 | iiim6/V7^1 | IV6/vim7^1 | V6/viidego7^1 | vim6/IM7^1 | viideg6/iim7^1 |
| 3-3-3 | IM7 | iim7 | iiim7 | IVM7 | V7 | vim7 | viidego7 |
| 3-3-4 | I+9 | ii+9 | iii+9 | IV+9 | V+9 | vi+9 | viideg+9 |
| 3-4-2 | I9-5 | ii9-5 | iii9-5 | IV9-5 | V9-5 | vi9-5 | viideg9-5 |
| 4-3-3 | I9-3 | ii9-3 | iii9-3 | IV9-3 | V9-3 | vi9-3 | viideg9-3 |
| 4-4-4 | Iq7 | iiq7 | iiiq7 | IVq7 | Vq7 | viq7 | viidegq7 |

## Key features

1. Degree + pattern = chord address -- no note names needed, just degree and pattern
2. Same pattern across all 7 degrees -- diatonic tuning auto-produces correct quality
3. 3-3-2 row has dual names -- e.g. degree 1 = I6 or vim7^1 depending on context
4. Inversions = starting position -- same hand shape, different degree
5. Augmented chords unavailable -- require lever changes
6. 9th chords omit one note -- 5 chord tones, 4 fingers: 9-3, 9-5, or +9
7. Quartal chords (4-4, 4-4-4) -- built in 4ths, notated Iq, iiq etc.
8. Only 2 physical shapes -- 3-finger skip-one and 4-finger skip-one

## TODO to extend

- Verify all cells by computing actual notes at each degree
- Add remaining 4-finger patterns: 3-4-3, 4-3-4, 4-4-3, 3-4-4, 4-3-2, 2-4-3 etc
- Verify dual-name cells are harmonically correct
- Add minor 6th chords and verify which patterns produce them
- Consider whether any cells in other rows have valid chord names as inversions
