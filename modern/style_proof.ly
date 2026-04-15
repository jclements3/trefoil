\version "2.22.0"

#(set-default-paper-size "letter")

\paper {
  top-margin = 1.5\cm
  bottom-margin = 1.5\cm
  left-margin = 2.0\cm
  right-margin = 2.0\cm
  between-system-padding = 0.4\cm
  #(define fonts
     (make-pango-font-tree
       "TeX Gyre Pagella"
       "TeX Gyre Pagella"
       "TeX Gyre Cursor"
       (/ staff-height pt 20)))
}

\markup { \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #4 "Chord-fraction style proof" }
\markup { \vspace #0.4 \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "Navy RH over burgundy LH; TeX Gyre Pagella Bold; Unicode quality glyphs (Delta, degree, o-slash); tightened kern." }
\markup { \vspace #1.2 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "V7 / I   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "iim7 / V   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "vii07 / vi   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "ø7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "IM7 / ii   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "Δ" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "IV / I   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "Is4 / V   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "iiim7 / IV   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "iii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "viio / I   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "IVM7 / V7   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "IV" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "Δ" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "iim11 / V7   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m11" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "vi / iii   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" } } \vspace #0.6 }
\markup { \hspace #2 \line { \override #'(font-name . "TeX Gyre Pagella") \fontsize #0 "V / I   " \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \vspace #0.6 }
