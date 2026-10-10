# 🎬 nCheck v0.6 - Autonomous Subtitle Technical Quality Control Panel

> **Technical inspection engine for SRT and ASS subtitle files based on MQM (Multidimensional Quality Metrics) standards.**

---

🇬🇧 **English** | [🇹🇷 Türkçe](README_TR.md)

![nCheck Interface](assets/interface1.png)
![nCheck Interface](assets/interface2.png)

## 📌 Overview

**Developer:** nutuzar
**Version:** v0.6 (Stable)
**License:** GPL-3.0

nCheck is a quality control (QC) tool that audits the technical compliance of SRT and ASS subtitle files according to international broadcasting standards (MQM). It does not interfere with the semantic or grammatical quality of the translation; its focus is strictly on readability, visual ergonomics, and technical layout.

Designed for those building massive subtitle archives, translators, and users looking to automate quality assurance (QA) workflows. It scans every loaded file to detect errors, calculates an objective quality score (0-100), and generates a sleek, interactive HTML dashboard report.

---

## 🚀 Core Features

* **Autonomous Multi-Layered Analysis:** The moment a file is dragged and dropped, it scans thousands of lines within milliseconds. While calculating an artisan quality score out of 100 based on the nCheck standard (19.5 CPS, 42 CPL, 84ms gap, 833ms minimum duration), it simultaneously performs an industrial compliance (Pass/Fail) audit according to the strict broadcasting standards of global platforms such as Netflix, Amazon, EBU, and OpenSubtitles.
* **Language-Agnostic Architecture & JSON Flexibility:** If you wish to use different technical limits for source files in other languages (e.g., German), you can effortlessly add these values as a new profile directly into the core JSON dictionary (INDUSTRY_PROFILES) of the system within seconds.

---

## 📊 Grading Scale

Based on the final calculated score (0-100), nCheck assigns one of the following classifications:

* `0 - 59` : 🔴 **REJECTED / POOR**
* `60 - 64`: 🟡 **MEDIOCRE**
* `65 - 69`: 🟡 **FAIR**
* `70 - 79`: 🟢 **WATCHABLE**
* `80 - 89`: 🟢 **GOOD**
* `90 - 94`: 🔵 **VERY GOOD**
* `95 - 100`: 🔵 **ARCHIVE QUALITY**

---

## 📜 nCheck Quality Evaluation Manifesto (MQM)

nCheck's scoring algorithm is based on global broadcast industry standards. The total 100 points are divided into three different centers of gravity (50%, 35%, 15%). Additionally, there is a Category 0 that operates independently of the score.


### ⛔ CATEGORY 0: Critical Errors (Unscored / Direct Rejection)
Violations in this category break fundamental broadcasting standards. Even if a file scores 99, if it contains any of the following errors, it directly falls into the **REJECTED** status:
* **Timecode Overlapping:** A subtitle block starting before the previous one has ended.
* **Multi-Line Violation:** The presence of 3 or more lines in a single subtitle block on the screen.
* **Negative Duration (Temporal Paradox):** A situation where a block's end time is earlier than its start time.

### 🔴 CATEGORY 1: Readability and Flow (Maximum 50 Points)
Measures the viewer's capacity to read the text without detaching from the film's pacing.
* **CPS Violation:** Exceeding the maximum Characters Per Second reading limit.
* **Flash Subtitles:** Text remaining on the screen for a duration too short for the human eye to perceive (e.g., under 0.7s).
* **Zombie Subtitles:** Text remaining on the screen unnecessarily long (e.g., over 7.0s).

### 🟡 CATEGORY 2: Visual Comfort and Layout (Maximum 35 Points)
The space the text occupies on the screen and its potential to cause eye strain are evaluated in this category.
* **CPL Violation:** Exceeding the Characters Per Line limit.
* **Frame Gap Violation:** The flicker effect caused by failing to leave a sufficient gap (e.g., 24ms) between two consecutive subtitles.
* **Pyramid Rule Violation:** A drastic difference in character counts between the upper and lower lines in a two-line block (vertical imbalance).

### 🟢 CATEGORY 3: Typographical Hygiene (Maximum 15 Points)
Inspects the typographical craftsmanship of the file. Fixed penalties per violation are applied rather than proportional deductions.
* Unnecessary double spaces between words.
* Illegal spaces placed before punctuation marks.
* Unclosed or incorrectly written HTML formatting tags (e.g., `<i>`, `<b>`).
* Misuse of ellipses (...) or illegal symbol usage.

---

## 🛠️ Installation and Usage

**Requirements:**
* Python 3.8+
* PyQt5
* pysrt

**Installation:**
Install the required dependencies:
```bash
pip install PyQt5 pysrt