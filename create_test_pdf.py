#!/usr/bin/env python3
"""Generate a test PDF with realistic content for TTS testing."""
from fpdf import FPDF

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_margins(20, 20, 20)

# --- Page 1 ---
pdf.add_page()
pdf.set_font("Helvetica", "B", 20)
pdf.cell(0, 12, "The Science of Sleep", ln=True, align="C")
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 8, "A Short Introduction", ln=True, align="C")
pdf.ln(10)

pdf.set_font("Helvetica", "B", 13)
pdf.cell(0, 8, "Chapter 1: Why We Sleep", ln=True)
pdf.ln(3)

pdf.set_font("Helvetica", "", 11)
body1 = (
    "Sleep is one of the most fundamental biological processes known to science. "
    "Every animal with a nervous system sleeps, from the fruit fly to the blue whale. "
    "Yet for centuries, we treated sleep as little more than an inconvenient interruption "
    "to our waking lives. That view has changed dramatically in recent decades."
)
pdf.multi_cell(0, 7, body1)
pdf.ln(4)

body2 = (
    "Researchers now understand that sleep is not a passive state. "
    "During the night, the brain is extraordinarily active - consolidating memories, "
    "clearing metabolic waste, regulating hormones, and repairing cellular damage. "
    "A single night of poor sleep impairs cognitive function by as much as 20 percent, "
    "e.g. reaction time, decision-making, and emotional regulation all suffer measurably."
)
pdf.multi_cell(0, 7, body2)
pdf.ln(4)

body3 = (
    "The average adult requires between 7 & 9 hours of sleep per night. "
    "However, modern society consistently undervalues rest. Studies show that "
    "approximately 35% of adults in developed nations sleep fewer than 6 hours "
    "on weekdays - a figure that has risen steadily since the 1950s."
)
pdf.multi_cell(0, 7, body3)

# Footer on page 1
pdf.set_y(-15)
pdf.set_font("Helvetica", "I", 8)
pdf.cell(0, 5, "The Science of Sleep - Introduction", align="C")

# --- Page 2 ---
pdf.add_page()
pdf.set_font("Helvetica", "I", 8)
pdf.cell(0, 5, "The Science of Sleep - Introduction", ln=True, align="C")
pdf.ln(5)

pdf.set_font("Helvetica", "B", 13)
pdf.cell(0, 8, "Chapter 2: The Stages of Sleep", ln=True)
pdf.ln(3)

pdf.set_font("Helvetica", "", 11)
body4 = (
    "Sleep is not a single uniform state. It is composed of several distinct stages "
    "that cycle throughout the night, each serving different physiological purposes. "
    "Scientists classify sleep into two broad categories: REM (Rapid Eye Movement) sleep "
    "and non-REM sleep. Non-REM sleep is further divided into 3 stages, i.e. N1, N2, and N3."
)
pdf.multi_cell(0, 7, body4)
pdf.ln(4)

body5 = (
    "N1 is the lightest stage, the transition from wakefulness. N2 follows and accounts "
    "for roughly 50% of total sleep time in healthy adults. During N2, the brain produces "
    "characteristic bursts of activity known as sleep spindles, which are thought to play "
    "a role in memory consolidation - particularly for procedural skills vs. declarative facts."
)
pdf.multi_cell(0, 7, body5)
pdf.ln(4)

body6 = (
    "N3, sometimes called slow-wave or deep sleep, is the most restorative stage. "
    "Growth hormone is released almost exclusively during N3, making it critical for "
    "physical repair and development. Children spend far more time in N3 than adults - "
    "a pattern that reflects their higher growth & repair requirements."
)
pdf.multi_cell(0, 7, body6)
pdf.ln(4)

body7 = (
    "REM sleep is when most vivid dreaming occurs. The brain during REM is nearly as "
    "active as during waking life, while the body's voluntary muscles are temporarily "
    "paralysed - a protective mechanism that prevents us from acting out our dreams. "
    "A complete sleep cycle from N1 through to REM takes approximately 90 minutes, "
    "and a full night contains 4 to 6 such cycles."
)
pdf.multi_cell(0, 7, body7)

# Footer on page 2
pdf.set_y(-15)
pdf.set_font("Helvetica", "I", 8)
pdf.cell(0, 5, "The Science of Sleep - Introduction", align="C")

# Page number
pdf.set_y(-10)
pdf.set_font("Helvetica", "", 8)
pdf.cell(0, 5, "2", align="C")

# --- Page 3 ---
pdf.add_page()
pdf.set_font("Helvetica", "I", 8)
pdf.cell(0, 5, "The Science of Sleep - Introduction", ln=True, align="C")
pdf.ln(5)

pdf.set_font("Helvetica", "B", 13)
pdf.cell(0, 8, "Chapter 3: The Consequences of Sleep Deprivation", ln=True)
pdf.ln(3)

pdf.set_font("Helvetica", "", 11)
body8 = (
    "The consequences of chronic sleep deprivation extend far beyond feeling tired. "
    "Epidemiological studies consistently link short sleep duration with increased risk "
    "of obesity, type 2 diabetes, cardiovascular disease, and certain cancers. "
    "The mechanisms are increasingly well understood at the molecular level."
)
pdf.multi_cell(0, 7, body8)
pdf.ln(4)

body9 = (
    "Perhaps the most alarming finding is the effect of sleep loss on the brain. "
    "A landmark 2019 study found that just one week of sleeping 6 hours per night "
    "produced cognitive deficits equivalent to 24 hours of total sleep deprivation. "
    "Critically, the sleep-deprived participants were largely unaware of their impairment - "
    "they rated their own performance as adequate, i.e. subjective and objective performance "
    "measures had completely decoupled."
)
pdf.multi_cell(0, 7, body9)
pdf.ln(4)

body10 = (
    "The good news is that sleep debt, at least in the short term, is recoverable. "
    "Two or three nights of adequate sleep can restore most cognitive functions to baseline. "
    "However, the idea that we can function on 5 hours on weekdays and \"catch up\" "
    "at the weekend is largely a myth. Some neurological processes require consistent "
    "nightly sleep and cannot be fully restored by weekend recovery alone."
)
pdf.multi_cell(0, 7, body10)
pdf.ln(4)

body11 = (
    "The 1st step toward better sleep hygiene is understanding what disrupts it. "
    "Caffeine has a half-life of approximately 5 to 7 hours, meaning a coffee consumed "
    "at 3pm still has 50% of its stimulant effect at 10pm. Alcohol, often mistakenly "
    "used as a sleep aid, suppresses REM sleep and leads to fragmented rest in the "
    "2nd half of the night."
)
pdf.multi_cell(0, 7, body11)

# Footer on page 3
pdf.set_y(-15)
pdf.set_font("Helvetica", "I", 8)
pdf.cell(0, 5, "The Science of Sleep - Introduction", align="C")
pdf.set_y(-10)
pdf.set_font("Helvetica", "", 8)
pdf.cell(0, 5, "3", align="C")

pdf.output("/Users/subhash/personal/playground/pdftospeech/test.pdf")
print("Created test.pdf")
