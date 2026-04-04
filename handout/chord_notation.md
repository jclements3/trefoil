# Harp Chord Notation

A terse but precise system for naming harp voicings. Every symbol encodes
something specific about the actual notes played and their order on the strings.
Names are generated algorithmically to be as short as possible while remaining
unambiguous.

---

## Format

```
root  quality  inversion  stack  removals  additions  octave
```

All fields except root are optional. Fields always appear in this order.

---

## Root and Quality

The root is a letter (C D E F G A B). Quality is implicit from the diatonic
context of C major — no extra symbol is needed for the most common quality.

| Symbol    | Meaning               | Example        | Notes                                 |
|-----------|-----------------------|----------------|---------------------------------------|
| uppercase | major triad           | `C` `F` `G`    | C F G are diatonic major roots        |
| `m`       | minor triad           | `Dm` `Em` `Am` | D E A are diatonic minor roots        |
| `°`       | diminished triad      | `B°`           | B is the diatonic diminished root     |
| `Δ`       | major 7th quality     | `CΔ` `FΔ`      | replaces the 7 symbol for major roots |
| `7`       | minor or dominant 7th | `Dm7` `G7`     | minor or dominant context             |
| `ø7`      | half-diminished 7th   | `Bø7`          | B diminished with minor 7th           |
| `s`       | sus4                  | `Cs`           | 4th replaces 3rd                      |
| `s2`      | sus2                  | `Cs2`          | 2nd replaces 3rd                      |

The diatonic quality of each root in C major:

| Root | Quality    |
|------|------------|
| C    | major      |
| D    | minor      |
| E    | minor      |
| F    | major      |
| G    | dominant   |
| A    | minor      |
| B    | diminished |

---

## Stack Level

The stack level is embedded in the base name and describes how far up the
tertian stack the chord extends. The stack is built by stacking thirds:
1 - 3 - 5 - 7 - 9 - 11 - 13.

| Name  | Stack           | Symbol                |
|-------|-----------------|-----------------------|
| Triad | 1 3 5           | `C` `Dm` `B°`         |
| 7th   | 1 3 5 7         | `CΔ` `Dm7` `G7` `Bø7` |
| 9th   | 1 3 5 7 9       | `CΔ9` `Dm9`           |
| 11th  | 1 3 5 7 9 11    | `CΔ11`                |
| 13th  | 1 3 5 7 9 11 13 | `CΔ13`                |

Sus stacks replace the 3rd with the 4th or 2nd:

| Name  | Stack     | Symbol      |
|-------|-----------|-------------|
| Sus4  | 1 4 5     | `Cs`        |
| Sus2  | 1 2 5     | `Cs2`       |
| 7sus4 | 1 4 5 7   | `G7s` `CΔs` |
| 7sus2 | 1 2 5 7   | `CΔs2`      |
| 9sus4 | 1 4 5 7 9 | `G9s`       |

---

## Inversions

A superscript number after the quality indicates which note of the stack is
in the bass (lowest string of the left hand).

| Symbol   | Meaning          | Example | Notes in order |
|----------|------------------|---------|----------------|
| *(none)* | root position    | `C`     | C E G          |
| `¹`      | first inversion  | `C¹`    | E G C          |
| `²`      | second inversion | `C²`    | G C E          |
| `³`      | third inversion  | `CΔ³`   | B C E G        |

The superscript refers to the position of the bass note within the stack list,
not the traditional figured-bass convention.

---

## Removals

A `-n` suffix means degree `n` from the stack is absent from the voicing.
Multiple removals are listed in ascending order.

| Symbol | Meaning           | Example | Notes            |
|--------|-------------------|---------|------------------|
| `-3`   | no third          | `C-3`   | C G (open fifth) |
| `-5`   | no fifth          | `C-5`   | C E              |
| `-5-3` | no third or fifth | —       | root only        |

Examples:

| Name     | Notes       | Explanation              |
|----------|-------------|--------------------------|
| `C-5`    | C E         | major triad missing 5th  |
| `C-5+6`  | C E A       | triad, drop 5th, add 6th |
| `CΔ9-5`  | C E B D     | major 9th stack, no 5th  |
| `CΔ13-5` | C F B E A D | major 13th, no 5th       |
| `CΔs-5`  | C F B       | sus4 major 7th, no 5th   |

---

## Additions

A `+n` suffix adds a degree that is not part of the chosen stack. The degree
number reflects the actual register: a 2nd above the octave is written `+9`,
not `+2`. Multiple additions are listed in ascending order.

| Symbol | Meaning                     |
|--------|-----------------------------|
| `+2`   | add 2nd (within the octave) |
| `+4`   | add 4th (within the octave) |
| `+6`   | add 6th (within the octave) |
| `+9`   | add 9th (above the octave)  |
| `+11`  | add 11th (above the octave) |
| `+13`  | add 13th (above the octave) |

The distinction between `+2` and `+9` depends on register: if the added note
appears above the point where the voicing has wrapped past the root, it is
named as the compound interval.

Examples:

| Name      | Notes   | Explanation                      |
|-----------|---------|----------------------------------|
| `C-5+6`   | C E A   | drop 5th, add 6th                |
| `C-5+6+9` | C F A D | drop 5th, add 6th, add 9th above |
| `CΔ-5+4`  | C F B E | major 7th, drop 5th, add 4th     |

---

## Octave Doubling

`+8` appended at the end means the lowest note of the voicing is doubled an
octave higher (i.e. the same note letter appears twice in the note list).

| Name   | Notes   | Explanation                              |
|--------|---------|------------------------------------------|
| `C+8`  | C E G C | root position triad, root doubled        |
| `C¹+8` | E G C E | first inversion, third doubled           |
| `C²+8` | G C E G | second inversion, fifth doubled          |
| `F²+8` | C F A C | F major, second inversion, fifth doubled |

---

## Algorithm

The name is chosen to be **as short as possible** while remaining unambiguous.
When multiple stack interpretations produce the same note set, the one yielding
the shorter name wins.

Example tie-breaking:

| Notes   | Candidate A        | Candidate B         | Winner   |
|---------|--------------------|---------------------|----------|
| C G B D | `CΔ9-3` (5 chars)  | `CΔs2` (4 chars)    | `CΔs2`   |
| C F B E | `CΔ-5+4` (6 chars) | `CΔs-5+3` (7 chars) | `CΔ-5+4` |

---

## Complete Examples

| Name      | Notes       | Reading                                 |
|-----------|-------------|-----------------------------------------|
| `C`       | C E G       | C major triad, root position            |
| `Dm¹`     | F A D       | D minor, first inversion                |
| `G7`      | G B D F     | G dominant 7th                          |
| `CΔ`      | C E G B     | C major 7th                             |
| `Bø7`     | B D F A     | B half-diminished 7th                   |
| `Cs`      | C F G       | C sus4                                  |
| `G7s`     | G C D F     | G dominant 7th sus4                     |
| `CΔs2`    | C D G B     | C major 7th sus2                        |
| `C²+8`    | G C E G     | C major, second inversion, root doubled |
| `C-5+6`   | C E A       | C major, no 5th, add 6th                |
| `C-5+6+9` | C F A D     | C major, no 5th, add 6th, add 9th       |
| `CΔ9-5`   | C E B D     | C major 9th, no 5th                     |
| `CΔ13-5`  | C F B E A D | C major 13th, no 5th                    |

---

## Harp-Specific Context

This notation describes **actual string order on the harp**, not abstract chord
theory. Notes are always listed ascending from the lowest string played. The
left hand plays the bottom portion of the chord, the right hand plays the top.

- No pinkies: maximum 4 fingers per hand
- Maximum 10-string span per hand
- LH thumb plays the 3rd or 4th note (not the root in most voicings)
- Gap between hands: 0–3 open strings

The voicing described by a name is always a specific ascending sequence of
strings, not a set of pitch classes.
