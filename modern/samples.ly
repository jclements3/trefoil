\version "2.22.0"

#(set-default-paper-size "letter")

\paper {
  top-margin = 0.90\cm
  bottom-margin = 0.90\cm
  left-margin = 1.20\cm
  right-margin = 1.20\cm
  between-system-space = 0.8\cm
  between-system-padding = 0.2\cm
  markup-system-spacing.padding = 0.4
  score-markup-spacing.padding = 0.3
  score-system-spacing.padding = 0.4
  system-system-spacing.padding = 0.5
  ragged-bottom = ##f
  ragged-last-bottom = ##f
  print-page-number = ##f
  #(define fonts
    (make-pango-font-tree
      "TeX Gyre Pagella"
      "TeX Gyre Pagella"
      "TeX Gyre Cursor"
      (/ staff-height pt 20)))
}

\book {
\bookpart {
\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "Jesus Loves Me" "key: Eb (4155)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 4/4 \tempo  4=120
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key ees \major     bes'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   g'4    g'4      f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } 
\bar "|"   g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   bes'4    bes'2  \bar "|"   c''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } }   
c''4    ees''4    c''4  \bar "|"   c''4      bes'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   bes'2  
\bar "|" \break    bes'4    g'4    g'4      f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } \bar "|"   g'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   bes'4    bes'2  \bar "|"   c''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } }   c''4      bes'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   ees'4  \bar "|"   g'4      f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }     ees'2 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } } \bar "|" \break    bes'2    g'4    bes'4  \bar "|"   c''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } } 
  ees''2.  \bar "|"   bes'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   g'4    ees'4  \bar "|"   g'4      
f'2. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } } \bar "|" \break    bes'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   g'4    bes'4  \bar "|"   
c''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   ees''2    c''4  \bar "|"   bes'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "IV" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "Δ" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }   ees'4   
 g'4.      f'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|"   ees'1 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } } \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "Silent Night" "key: Bb (4068)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 3/4 \tempo  4=60
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key bes \major     f'8. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   g'16    f'8    d'4.  \bar "|"   f'8.  
  g'16    f'8    d'4.  \bar "|"   c''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }   c''8    a'4.  \bar "|"   
bes'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   bes'8    f'4.  \bar "|" \break    g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } }   g'8    
bes'8.    a'16    g'8  \bar "|"   f'8. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }     g'16 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }     
f'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   d'4.  \bar "|"   g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   g'8    bes'8.      
a'16 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } }     g'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \bar "|"   f'8. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     
g'16 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }     f'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   d'4.  \bar "|" \break    c''4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   c''8    ees''8.    c''16    a'8  \bar "|"   bes'4. 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   d''4.  \bar "|"   bes'8    f'8    d'8      f'8. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } 
  ees'16      c'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|"   bes2. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "Away In A Manger" "key: F (4051)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 3/4 \tempo  4=100
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key f \major     c''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|"   c''4.    bes'8    a'4  
\bar "|"   a'4.    g'8    f'4  \bar "|"   f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   e'4    d'4  
\bar "|" \break    c'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   c'4  \bar "|"   c'4. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }   d'8    c'4  
\bar "|"   c'4    g'4    e'4  \bar "|"   d'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   c'4    f'4  
\bar "|" \break    a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   c''4  \bar "|"   c''4.    bes'8    a'4  \bar "|" 
  a'4.    g'8    f'4  \bar "|"   f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   e'4    d'4  \bar "|" \break    c'2 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   c'4  \bar "|"   bes'4. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }   a'8    g'4  \bar "|"   
a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   g'4    f'4  \bar "|"   g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" } }   d'4      e'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \bar "|" \break    f'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } } \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "At The Lamb's High Feast" "key: C (4146)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 4/4 \tempo  4=110
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key c \major     c'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   c'4  \bar "|"   g'4    c''4      b'8 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   a'16    g'16    a'8    a'8  \bar "|"   g'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }     
a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   a'4  \bar "|"   b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } }     a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } }     
g'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   a'8    g'8    f'8  \bar "|" \break    e'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" } }   e'8    
d'8      e'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   f'8  \bar "|"   g'8    g'8      c'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }  
 e'8      d'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" } }     e'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   c'8  \bar "|"   b8 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }     c'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     d'8 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }     f'8 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     e'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }   d'4  \bar "|"   c'2  \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "The Cloud Received Christ From Their Sight" "key: G (4114)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 3/2 \tempo  4=200
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key g \major   d'2  \bar "|"   g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   g'4      a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } 
  a'2  \bar "|"   b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }     a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }     g'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } } 
    a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "Δ" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } \bar "|"   b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   b'4      c''2 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }     b'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|" \break    a'1 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }   d''2  
\bar "|"   d''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   b'4    b'2    g'2  \bar "|"   g'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "IV" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } }   e'4    e'2    g'4    e'4  \bar "|"   d'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   g'4  
  g'2      a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|" \break    g'1 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "Jesus Wants All Of His Children" "key: D (4241)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 4/4 \tempo  4=100
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key d \major     fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   fis'4      fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" } }     e'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } \bar "|"   d'4      fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   b'4    a'4  \bar "|"   
d'4  \bar "|"   d''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   d''4    a'4    fis'4  \bar "|" \break    e'2. 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "Δ" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }   r4 \bar "|"   e'4      fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   g'4    a'4  
\bar "|"   b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   cis''4    d''4    fis'4  \bar "|"   e'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" } }     g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "IV" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } }     fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     e'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "iii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } } \bar "|" \break    d'2. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }   r4 \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "Let Children Hear The Mighty Deeds" "key: A (4299)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 4/4 \tempo  4=100
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key a \major     e'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|"   cis''4    a'4      fis'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     e'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } } \bar "|"   a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }     b'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } }     cis''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }     e''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } } \bar "|"   cis''4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }     a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     fis'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "Eb" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "Eb" } } \bar "|" \break    e'2. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }   b'8    cis''8  \bar "|"   d''4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }     d''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     cis''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "Δ" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }   a'4  
\bar "|"   fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     gis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" } } 
  e''8    d''8  \bar "|"   cis''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } }     cis''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     
b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } }     gis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" } } \bar "|" \break    a'2. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } 
\bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "Tis Good, Lord, To Be Here" "key: E (4084)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 2/4 \tempo  4=100
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key e \major     e'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|"   fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }     a'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } } \bar "|"   gis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } } \bar "|"   
e'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } } \bar "|" \break    cis''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } }   e''4  
\bar "|"   dis''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }     cis''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "Bb" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "Bb" } } \bar "|"   b'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }     gis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } } \bar "|"   a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   cis''4  
\bar "|" \break    b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } } \bar "|"   gis'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "IV" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } }     ais'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } } \bar "|"   b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } }     e'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } } \bar "|"   fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   a'4  \bar "|" \break    gis'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }     fis'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" } } \bar "|"   e'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } } \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "O For A Thousand Tongues" "key: G (4175)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 3/2 \tempo  4=200
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key g \major   d'2  \bar "|"   g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   g'4      a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } 
  a'2  \bar "|"   b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }     a'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }     g'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" } } 
    a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "Δ" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } \bar "|"   b'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   b'4      c''2 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }     b'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|" \break    a'1 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }   d''2  
\bar "|"   d''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   b'4    b'2    g'2  \bar "|"   g'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "IV" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s2" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } }   e'4    e'2    g'4    e'4  \bar "|"   d'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   g'4  
  g'2      a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|" \break    g'1 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

\markup {
    \override #'(font-name . "TeX Gyre Pagella Bold")
    \fontsize #2
    \fill-line { "Now the Light Has Gone Away" "key: F (4313)" }
}
\score {
  \new Staff \with {
    \override VerticalAxisGroup.staff-staff-spacing.padding = 3
  } {
    \override Score.BarNumber.break-visibility = ##(#f #f #f)
    \set Score.defaultBarType = ""

\time 4/4 \tempo  4=100
 % %pagewidth 200cm
 % %continueall 1
 % %leftmargin 0.5cm
 % %rightmargin 0.5cm
 % %topspace 0
 % %musicspace 0
 % %writefields Q 0
 \key f \major     f'4. ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "ii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }   f'8    f'4    f'4  \bar "|"   e'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }     f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     g'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \bar "|"   g'4    g'4 
   g'4      g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } } \bar "|"   f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "I" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "s4" } \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } }     g'4 
^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "V" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "7" } } }     a'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|" \break    a'4.    a'8    a'4    a'4  
\bar "|"   g'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }     f'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vi" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     d''2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" } } 
\bar "|"   c''4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "IV" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "vii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "°" } } }   a'4    c''4      bes'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "vi" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" } } \bar "|" 
  d'4      e'4 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "I" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \concat { \bold "ii" \hspace #-0.3 \raise #1.1 \fontsize #-1 \bold "m7" } } }     f'2 ^\markup { \override #'(baseline-skip . 2.80) \left-column { \with-color #(rgb-color 0.122 0.306 0.475) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "iii" \with-color #(rgb-color 0.482 0.169 0.169) \override #'(font-name . "TeX Gyre Pagella Bold") \fontsize #2 \bold "V" } } \bar "|."

  }
  \layout {
    #(layout-set-staff-size 15)
    ragged-right = ##f
    ragged-last = ##t
    \context {
      \Score
      \override TextScript.outside-staff-priority = #100
      \override TextScript.padding = #1.5
      \override TextScript.staff-padding = #3.0
      \override MetronomeMark.outside-staff-priority = #1000
      \override MetronomeMark.padding = #2.0
      \override TextScript.direction = #UP
      \override TextScript.avoid-slur = #'outside
      \override SpacingSpanner.base-shortest-duration = #(ly:make-moment 1/8)
      \override SpacingSpanner.uniform-stretching = ##t
    }
  }
}

}
}
