# Feature: Audio Capture

When an attendee drops a coin, Narly plays a chime, starts listening the instant it ends, and
turns what it heard into the question the fortune is written from. If it hears nothing usable,
it asks itself a question instead and carries on, so the attendee still receives a fortune. The
ticket looks the same either way, but the log does not: every fortune records what Narly heard,
or which way hearing failed, and whether the question was substituted.

**Source**: `_work/shipped/capture-measure-and-fix/spec.md`. Earlier behavior was reverse-engineered
from code (2026-09-22) and has since been checked against tests and by hand.
**Last verified**: 2026-09-28

---

## Increments

- [x] 2026-09-28 — Measure and fix attendee capture (`_work/shipped/capture-measure-and-fix/spec.md`)
- [ ] Live baseline: the directional mic on a stand, fixture clips recorded across quiet,
      conversation, and leaning-in, and a first measured success rate (no spec yet)
- [ ] Pi port: persistent logs, a service that restarts Narly, stable device names (no spec yet)
- [ ] Endpointing and recognition: voice detection in place of the loudness threshold, and a
      better recognizer with a local fallback (no spec yet)

---

## Open Issues

Open issues are genuine defects or gaps, not documentation holes. Resolved ones stay listed with
the commit that fixed them, so the reasoning isn't lost.

1. **Resolved in `32daedb`: ambient-noise calibration was performed and then discarded.** A fixed
   threshold of `1100` with adaptation off overwrote the room measurement on every run. Narly now
   keeps the measurement, uses the speech library's default threshold, and adapts to the room as
   it goes.

2. **`TIMEOUT_RECORDING` still does not control the listening window it documents.** Listening
   uses fixed values (10 seconds to start speaking, 8 seconds of speech). The constant only
   feeds the 25-second outer guard. *This increment:* unchanged, on purpose. It belongs with the
   endpointing-and-recognition increment, which replaces how listening decides to stop.
   (`serial_trigger.py:43`, `serial_trigger.py:147`, `serial_trigger.py:271`)

3. **A failed capture still looks like a successful one on the ticket.** Every failure prints a
   plausible fortune for the persona's default question, and the attendee is told nothing.
   *This increment:* failures are now told apart in the log. Each has its own outcome name, and
   a substituted question is marked as substituted (`7c94a8a`). The ticket is unchanged, by
   decision.

4. **Resolved in `32daedb`: a ~2.8 second dead window after the coin lost the start of
   questions.** Calibration used to run after the chime, so attendees who spoke as the chime
   ended lost their first words. Calibration now runs before the chime, and listening starts the
   instant the chime ends.

5. **The app occasionally hangs, and the cause is unknown.** *This increment:* the log now
   exists to diagnose it. Each fortune's capture line records how long hearing took, and the
   next hang will show where the run stopped. One candidate is gone: `afplay` was replaced by
   in-process playback whose blocking wait gives up after 5 seconds (`2114bf5`). One candidate
   is now confirmed from the code. When the whole listening stage passes 25 seconds, Narly
   records `overrun` but still waits for the stuck attempt to finish before carrying on
   (`capture_client.py:128-134`). The speech recognizer call has no timeout of its own, so a
   recognizer that never answers would hold the booth. Whether that is what happened at the
   events is still unconfirmed.

6. **An offline clip run proves the clip can be read, not what is heard in it.** With
   `--offline`, the stand-in recognizer ignores the recording and reports the persona's default
   question. So the log never shows the clip's own question, and "the same clip gives the same
   heard text" holds only trivially. Proving what Narly hears in a clip needs a recognizer that
   runs offline for free. That belongs with the endpointing-and-recognition increment, alongside
   the fixture clips the live-baseline increment records.

7. **The readiness chime may be too quiet in a busy room.** At the September events it was
   marginal over crowd noise, and people leaned in to hear it. In-process playback tops out at
   full volume, so the old 3× boost is gone (`2114bf5`) and the chime may now be quieter. A guest
   who misses the chime has only the lights glowing to tell them to speak. Check it at the live
   baseline: the chime at the real speaker's volume, over conversation, from where a guest
   stands.

---

## Behaviors

### Rule: Narly signals that it is ready, then listens the instant the signal ends

```scenario
Scenario: The chime plays, then listening begins
  Given an attendee has dropped a coin
  When Narly prepares to hear their question
  Then the lights glow
  And Narly measures the room's noise
  And a chime plays and finishes
  And Narly begins listening immediately after the chime ends
```

```scenario
Scenario: An attendee who speaks as the chime ends is heard from the first word
  Given an attendee has learned to speak the moment the chime finishes
  When they begin "Will I find treasure today?" as the chime ends
  Then the whole question is recorded, including "Will"
```

*Field-verified 2026-09-28 (Fifine AM8 USB mic, arm's length):* a question spoken right after
the chime was transcribed starting with its first word.

*Field-verified 2026-09-22:* the chime is audible in a quiet room, and attendees learned to treat
it as their cue to speak. In a busy room it is marginal, and people crane toward the cabinet to
catch it. Its timing is now fixed; its loudness is not (Open Issue 7).

```scenario
Scenario: The thinking cue follows once the question is captured
  Given Narly has finished listening
  When it starts writing the fortune
  Then the thinking cue plays
  And the fortune is written while the cue is still playing
```

### Rule: Narly wakes to an ordinary voice and adjusts to the room

```scenario
Scenario: A normal speaking voice is enough
  Given an attendee standing at arm's length from the microphone
  When they ask their question at conversational volume, without leaning in
  Then Narly records the question
  And the log shows it as heard
```

```scenario
Scenario: Narly adjusts to the room rather than a fixed setting
  Given the room was quiet in the morning and has conversation in it by afternoon
  When an attendee asks a question in the afternoon at the same volume as the morning
  Then Narly still begins recording
```

```scenario
Scenario: A question that ends softly is heard to the end
  Given Narly measured the room when the coin dropped
  When an attendee's voice drops on the last word of the question
  Then Narly keeps recording until the attendee actually stops
  And the last word is in what Narly heard
```

### Rule: A question Narly hears is the question the fortune answers

```scenario
Scenario: A clearly spoken question is used and recorded
  Given an attendee asks "Will I find treasure today?"
  And Narly hears it clearly
  When the fortune is generated
  Then it is generated from "Will I find treasure today?"
  And the log shows that question as heard, word for word
```

### Rule: When Narly hears nothing usable, it asks itself a question instead, and says so

```scenario
Scenario: Silence is replaced with Narly's own question
  Given an attendee drops a coin and says nothing
  When Narly gives up listening after 10 seconds
  Then the thinking cue plays as normal
  And it proceeds using the question "What is my fortune for today?"
  And the attendee still receives a printed fortune
  And nothing on the ticket indicates the question was substituted
  But the log records that nothing was heard and that the question was substituted
```

*Field-verified 2026-09-22:* this path does not hang. The thinking cue sounds and a generic
fortune prints.

```scenario
Scenario: An unintelligible answer is replaced the same way
  Given an attendee speaks but Narly cannot make out the words
  When Narly gives up on the recording
  Then it proceeds using the question "What is my fortune for today?"
  And the attendee receives a fortune that looks the same as a heard one
  But the log records the answer as "not understood", not as silence
```

### Rule: The operator can tell every way of failing to hear apart

```scenario
Scenario: Silence and an unintelligible answer are different records
  Given one attendee dropped a coin and never spoke
  And another attendee's words could not be made out
  When the operator reads the log
  Then the first run is recorded as "nothing heard"
  And the second is recorded as "not understood"
```

```scenario
Scenario: Two different failures look the same to attendees but not to the operator
  Given one attendee is misheard because the room is loud
  And another attendee is not heard because the microphone is unplugged
  When each of them collects their fortune
  Then neither is told anything went wrong
  But the log records one as "not understood" and the other as a microphone fault
```

```scenario
Scenario: Counting an event's failures by kind
  Given Narly served 60 attendees across a day, with the log saved to a file
  And 18 of them were not heard correctly
  When the operator counts the log's outcomes
  Then they can count 18 failures
  And they can see how many were silence, not understood, the recognizer unreachable, a
    microphone fault, or the whole stage overrunning
```

```scenario
Scenario: Failures stand out from ordinary progress
  Given a day of fortunes, some heard and some not
  When the operator reads the log
  Then every line carries its time and a severity
  And a failed capture is a warning while a heard one is ordinary information
```

### Rule: The operator's live view shows each fortune as a timestamped run

```scenario
Scenario: Watching fortunes happen on the laptop
  Given the operator is watching Narly's terminal during an event
  When an attendee drops a coin
  Then a coin line starts that fortune's run
  And every line after it shows its time and severity
  And the capture line shows what was heard, or why nothing was
```

Every terminal line now carries a timestamp and a level, and the blank lines that used to
separate cycles are gone. The coin line is what marks where each fortune starts.

### Rule: Listening ends on its own without the attendee doing anything

```scenario
Scenario: An attendee who never speaks is not waited on forever
  Given an attendee drops a coin and stays silent
  When 10 seconds pass after the chime with no speech
  Then Narly stops listening
```

```scenario
Scenario: A long-winded question is cut off
  Given an attendee begins speaking
  When they have been speaking for 8 seconds
  Then Narly stops listening and works with what it has
```

*Observed 2026-09-28:* on a colleague's laptop, two real-mic questions both recorded for the
full 8 seconds rather than stopping at the end of the question.

```scenario
Scenario: A pause mid-question does not end the recording
  Given an attendee says "Will I find treasure" and pauses to think
  When the pause lasts less than 1.5 seconds
  Then Narly keeps listening for the rest of the question
```

### Rule: A tester needs no hardware and spends nothing

```scenario
Scenario: A tester runs a fortune from typed text
  Given a tester on their own laptop with no microphone, coin slot, or printer attached
  When they run an offline fortune with the typed question "Should I take the job?"
  Then the run completes with a test ticket on screen
  And the log shows "Should I take the job?" as the question heard
  And no call was made to the paid transcription or fortune services
```

```scenario
Scenario: A tester runs a fortune from a recorded clip
  Given a tester with no hardware attached
  And a recorded clip of someone asking "Should I take the job?"
  When they run an offline fortune using that clip
  Then the run completes with a test ticket on screen
  And the log shows the persona's usual question as the question heard
  And no call was made to the paid transcription or fortune services
```

*Field-verified 2026-09-28:* a colleague who had never run Narly followed `docs/testing.md` on
her own Mac and ran both, with no hardware and no API key. The clip's own words don't reach the
log offline; see Open Issue 6.

```scenario
Scenario: A tester with no hardware doesn't need to name a question
  Given a tester with no hardware attached
  When they run an offline fortune without typing a question or giving a clip
  Then Narly uses the persona's usual question as typed text
  And the run completes without opening a microphone
```

### Rule: The same input gives the same record every time

```scenario
Scenario: Replaying a typed question is repeatable
  Given a tester runs the offline typed question "Will I find treasure today?"
  When they drop two coins in a row
  Then both runs record the same outcome and the same heard text
  And both record the same question
```

### Rule: The attendee's experience of a heard fortune is unchanged

```scenario
Scenario: A successful fortune looks and sounds the same
  Given an attendee drops a coin, waits for the chime, and asks "What is my fortune?"
  Then they hear the same chime and thinking cue as before
  And they see the same light states as before
  And they receive a printed ticket no wider than 32 characters, in every persona
```

---

## Edge Cases

### Rule: Narly recovers from every capture failure rather than stopping

```scenario
Scenario: The transcription service cannot be reached
  Given the booth has lost its internet connection
  When an attendee asks a question
  Then Narly does not crash
  And the log records the recognizer as unreachable
  And the fortune run continues with the substituted question
```

```scenario
Scenario: The microphone is unavailable
  Given the microphone has been unplugged from the laptop
  When an attendee drops a coin and speaks
  Then Narly does not crash
  And the log records a microphone fault, with the reason
  And the fortune run continues with the substituted question
```

```scenario
Scenario: The whole listening stage overruns
  Given transcription is slow to return
  When more than 25 seconds have passed since listening began
  Then the log records the attempt as overrun, with how long it really took
  And the fortune run continues with the substituted question once the attempt ends
```

> The attempt is not cut off at 25 seconds. Narly waits for it to finish, then records it as
> overrun (Open Issue 5).

```scenario
Scenario: A recognizer that returns no words is not counted as heard
  Given the recognizer answers with an empty transcript
  When Narly records the capture
  Then it is recorded as "not understood"
  And the question is substituted
```

### Rule: In a very quiet room, silence is recorded as "not understood"

```scenario
Scenario: Silence at a quiet desk
  Given Narly is running in a silent room, such as an office desk
  When an attendee drops a coin and says nothing
  Then within a few seconds Narly treats the microphone's own faint hiss as the start of speech
  And the capture is recorded as "not understood", not "nothing heard"
  And the fortune run continues with the substituted question
```

*Not re-measured since the level has been held while listening (2026-09-28); silence may now
be recorded as "nothing heard" instead.* *Measured 2026-09-28:* with adaptation on, the threshold falls to about 1.5 times the mic's hiss
within about 2.4 seconds, and the hiss then trips it. A festival hall is never this quiet. The
endpointing-and-recognition increment replaces the threshold.

### Rule: Missing or broken sound never stops a fortune

```scenario
Scenario: A cue file is missing
  Given the chime's sound file has been deleted
  When an attendee drops a coin
  Then no chime plays
  And the log records the missing file
  And the fortune run continues
```

```scenario
Scenario: The speaker never reports the chime finished
  Given the sound device starts the chime but never reports it done
  When 5 seconds have passed
  Then Narly stops the chime and records it as stuck
  And listening begins
```

```scenario
Scenario: The next coin cuts off the previous thinking cue
  Given the thinking cue from one fortune is still playing
  When the next attendee drops a coin
  Then the new chime replaces the thinking cue
```

### Rule: The record stays readable whatever is said

```scenario
Scenario: An attendee's words cannot break the record
  Given an attendee says something containing quotation marks and a line break
  When the operator reads the log
  Then that fortune's capture is still one line
  And it can still be counted with the others
```

```scenario
Scenario: The log file does not grow without limit
  Given Narly is saving its log to a file
  When the file reaches 5 megabytes
  Then it starts a new file, keeping the three most recent older ones
```

```scenario
Scenario: A log file that can't be written doesn't stop Narly
  Given the operator asks for a log file in a folder that doesn't exist
  When Narly starts
  Then it reports the problem once
  And it keeps logging to the terminal
```

---

## Test Coverage

| Scenario | Test File | Status |
|----------|-----------|--------|
| The chime plays, then listening begins | `tests/test_sequencing.py:L61` (measure → chime → listen order; the lights are checked by hand) | Covered |
| An attendee who speaks as the chime ends is heard from the first word | — (manual: first word heard with the AM8, 2026-09-28; the order behind it is `tests/test_sequencing.py:L61`) | Not covered |
| The thinking cue follows once the question is captured | `tests/test_audio_out.py:L32` | Covered |
| A normal speaking voice is enough | — (manual: arm's-length check with the AM8, Step 8) | Not covered |
| Narly adjusts to the room rather than a fixed setting | — (`tests/test_sequencing.py:L69` asserts the measurement is kept; the room is measured on every coin; a room changing through the day is unmeasured) | Not covered |
| A question that ends softly is heard to the end | — (`tests/test_sequencing.py:L69` asserts the level is held while listening; manual: baseline rerun 2026-09-28, end cut-offs 4 → 1 in 20) | Not covered |
| A clearly spoken question is used and recorded | `tests/test_on_coin_event.py:L65` | Covered |
| Silence is replaced with Narly's own question | `tests/test_on_coin_event.py:L37` | Covered |
| An unintelligible answer is replaced the same way | `tests/test_on_coin_event.py:L87` | Covered |
| Silence and an unintelligible answer are different records | `tests/test_on_coin_event.py:L37`, `tests/test_on_coin_event.py:L87` | Covered |
| Two different failures look the same to attendees but not to the operator | `tests/test_on_coin_event.py:L87`, `tests/test_on_coin_event.py:L105` | Covered |
| Counting an event's failures by kind | — (manual: `grep -c` recipes in `docs/testing.md`, checked against a real log file 2026-09-28) | Not covered |
| Failures stand out from ordinary progress | `tests/test_logger.py:L27`, `tests/test_on_coin_event.py:L87` | Covered |
| Watching fortunes happen on the laptop | `tests/test_on_coin_event.py:L222`, `tests/test_logger.py:L27` | Covered |
| An attendee who never speaks is not waited on forever | `tests/test_capture_client.py:L43` (outcome only; the 10 seconds is the library's) | Not covered (code-derived) |
| A long-winded question is cut off | — | Not covered (code-derived) |
| A pause mid-question does not end the recording | — (`tests/test_sequencing.py:L77` asserts the 1.5-second setting; the pause behavior is the library's) | Not covered (code-derived) |
| A tester runs a fortune from typed text | `tests/test_replay.py:L63` | Covered |
| A tester runs a fortune from a recorded clip | `tests/test_replay.py:L40` (file becomes audio; the full run checked by a colleague 2026-09-28) | Not covered |
| A tester with no hardware doesn't need to name a question | `tests/test_replay.py:L100` | Covered |
| Replaying a typed question is repeatable | `tests/test_replay.py:L63` | Covered |
| A successful fortune looks and sounds the same | — (`tests/test_smoke.py:L23` asserts the 32-character width for every persona; sound and lights are checked by hand) | Not covered |
| The transcription service cannot be reached | `tests/test_on_coin_event.py:L164` | Covered |
| The microphone is unavailable | `tests/test_on_coin_event.py:L248` | Covered |
| The whole listening stage overruns | `tests/test_on_coin_event.py:L187` | Covered |
| A recognizer that returns no words is not counted as heard | `tests/test_capture_client.py:L151` | Covered |
| Silence at a quiet desk | — (manual: measured with the AM8, 2026-09-28) | Not covered |
| A cue file is missing | `tests/test_audio_out.py:L50` | Covered |
| The speaker never reports the chime finished | `tests/test_audio_out.py:L73` | Covered |
| The next coin cuts off the previous thinking cue | — | Not covered (code-derived) |
| An attendee's words cannot break the record | `tests/test_on_coin_event.py:L129` | Covered |
| The log file does not grow without limit | `tests/test_logger.py:L49` | Covered |
| A log file that can't be written doesn't stop Narly | `tests/test_logger.py:L111` | Covered |

Cues on a Linux machine (the spec's acceptance criterion 8) aren't a scenario here yet. They
are checked on the Pi in the Pi-port increment.

<!-- Status vocabulary. Each status is a claim about what is proved, not a stage in a process:
     read a row as its answer to "what does this entitle me to believe?"

     FOUR STATUSES RECORD AN OBSERVATION — what was seen, or that nothing was:

     - Covered: a test asserts this scenario, and its last run passed.
     - Test failing: a test asserts this scenario, and its last run did not pass. Named for what was
       observed rather than for its cause, because the cause may be behavior not built yet, a
       regression, or a doc that is simply wrong, and the row cannot tell those apart. Whatever
       reported the run is where the cause gets argued.
     - Not covered: the scenario is specified, and nothing asserts it.
     - Not covered (code-derived): the rule was inferred by reading the code — never specified and
       never tested, and so the weakest claim in this table.

     ONE STATUS RECORDS A DECISION, and it is the only one a person writes deliberately:

     - Ruled out — <reason>: the project has decided this scenario cannot be proved here, and
       the reason travels in the row so a later reader can judge whether it still holds.

     The split is the point. The four above say what happened; this one says somebody chose — the
     difference between a gap nobody has reached yet and a gap the project decided to live with. It is
     named unlike the other four on purpose: an earlier draft called it "Not coverable", which sat one
     syllable from "Not covered" and was misread as an ordinary gap every time somebody skimmed the
     table. A status that records a decision should not look like a status that records an absence. -->

---

## Revision Notes

- 2026-09-22: Initial draft reverse-engineered from `record_and_transcribe()` and its call site
  in `serial_trigger.py` — not yet human-verified.
- 2026-09-22: Owner review against two events' field experience. Confirmed the chime is audible
  but marginal in noise and that attendees learned to speak on it; confirmed a failed capture
  does not hang and prints a generic fortune. Added the ~2.8s dead window (Open Issue 4), the
  unexplained hangs (Open Issue 5), and a rule separating timing losses from noise losses.
  Recorded that tuning the energy threshold and the recording timeout produced no observed
  effect, which matches Open Issues 1 and 2.
- 2026-09-28: Updated for the measure-and-fix-capture increment; draft banner removed.
  - **Listening now starts as the chime ends.** The spec's scenario said "as the chime starts".
    It now says "as the chime ends": listening during the chime would record the chime itself
    as speech, and attendees in the field speak as it ends. The old "opening of the question is
    lost" scenario is gone, because that no longer happens.
  - **Default threshold, adapting.** Narly now uses the speech library's default wake threshold
    and adjusts it to the room.
  - **Failures are on the record.** What was heard, or which of the five failures occurred, is
    in the log, along with whether the question was substituted.
  - **Hardware-free testing.** A tester with no hardware can run a fortune from typed text or a
    clip.
  - **Operator's live view.** The spec said it "behaves as it does today", which is no longer
    true: every terminal line now carries a time and level, the blank lines between cycles are
    gone, and the coin line marks each fortune's start.
  - **Open Issues.** 1 and 4 resolved in `32daedb`. 2, 3, and 5 remain open, with this
    increment's effect noted. 5 gains a confirmed candidate from the code: an overrun waits for
    the stuck attempt. 6 is new: offline clips don't prove what's heard. 7 is new: the chime's
    loudness in a busy room, carried from the 2026-09-22 field check.
  - **Evidence.** The coverage table now points at real tests. Recognizer-unreachable, overrun,
    and coin-line-order scenarios gained full-run tests at review, so all five failure kinds are
    proved end to end. The hardware-only scenarios name
    their manual check. Quiet-desk silence logs "not understood", as measured on 2026-09-28.
- 2026-09-28: **The wake level is held while listening.** Narly still measures the room on every
  coin, but it no longer raises the level mid-question. Adapting had cut off softer last words.
  In the first baseline (20 solo questions on the laptop) that cost 4 of 8 misses; with the level
  held, the same 20 scored 95% against 60%, with one end cut-off left. The four first-word losses
  went too, for a reason not yet understood. Added the "ends softly"
  scenario. The quiet-desk silence note is unverified since this change.
