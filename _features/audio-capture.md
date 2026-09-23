# Feature: Audio Capture

When an attendee drops a coin, Narly plays a cue, listens for their spoken question, and turns
what it heard into the text the fortune is written from. If it hears nothing usable, it quietly
asks itself a question instead and carries on — the attendee still receives a fortune, and
nothing on the machine distinguishes that from a question Narly actually heard.

> **Draft** — Reverse-engineered from code; these scenarios have not been verified against a
> running implementation or any test. Refine and verify before relying on them.

**Source**: derived from implementation (2026-09-22) — no originating spec; reverse-engineered
from code.
**Last verified**: 2026-09-22

---

## Increments

- [ ] (no shipped increments recorded — reverse-engineered baseline)

---

## Open Issues

Three findings from reading the implementation. Each is a genuine defect or dead code rather
than a documentation gap, and all three bear on the capture-quality problem reported after the
first two events.

1. **Ambient-noise calibration is performed and then discarded.**
   `recognizer.adjust_for_ambient_noise(source, duration=0.8)` measures the room and sets
   `energy_threshold` from it. The next two lines overwrite `energy_threshold` with the fixed
   value `1100` and set `dynamic_energy_threshold = False`, so the measurement is thrown away
   unused. The calibration costs 0.8 seconds of every run and changes nothing. Its inline
   comment also claims it runs "while sound plays", but the cue above it is played with
   `wait=True`, so the sound has already finished — calibration happens in silence, measuring an
   empty room rather than the festival.

   **This matches what the owner observed in the field.** Long sessions spent tuning the fixed
   `1100` produced no reliable improvement. A plausible reading: a single fixed threshold is
   being asked to serve a room whose noise floor moves through the day, while the one mechanism
   that would track that movement is computed and discarded on every run. Tuning hunts a stable
   value for a moving target. Treat this as a hypothesis to test once logging exists, not as an
   established cause.
   (`serial_trigger.py:90-95`)

2. **`TIMEOUT_RECORDING` does not control the listening window it documents.**
   The constant is commented "Max time to wait for speech input" and set to 15 seconds, but the
   actual call uses hardcoded values — `listen(source, timeout=10, phrase_time_limit=8)`. The
   constant only feeds the outer guard (`TIMEOUT_RECORDING + 10` = 25s). Raising it to give
   attendees longer to speak would have no effect on how long Narly actually listens. The owner
   reports tuning this constant and seeing no change in behaviour, which is exactly what the code
   predicts.
   (`serial_trigger.py:37`, `serial_trigger.py:99`, `serial_trigger.py:126`)

3. **A failed capture is indistinguishable from a successful one after the fact.**
   All five failure paths return `None`, and the caller silently substitutes the persona's
   `default_question`. The run then proceeds normally and prints a plausible fortune. Nothing is
   recorded, so an operator cannot tell afterwards whether a fortune answered the attendee's
   question or Narly's own. This is the mechanism behind "it was unclear whether the audio was
   captured accurately" — the design makes it structurally unclear.
   (`serial_trigger.py:105-116`, `serial_trigger.py:238-240`)

4. **There is a ~2.8 second dead window after the coin in which speech is lost.**
   The readiness chime (`sfx_magic.mp3`, 1.96s) is played with `wait=True`, so it blocks. Only
   after it finishes does the 0.8s ambient calibration run, and only then is `listen()` called.
   Anything the attendee says in those ~2.8 seconds is never recorded. This interacts badly with
   observed attendee behaviour: people learned to treat the chime as their cue and begin speaking
   as it ends, which places the start of their question inside the calibration gap. The cue
   trains exactly the wrong timing.
   (`serial_trigger.py:86`, `serial_trigger.py:90`, `serial_trigger.py:99`)

5. **The app occasionally hangs, and the cause is unknown.**
   Reported from the first two events, with no pattern identified and nothing recorded at the
   time to narrow it down. A failed capture is *not* the cause — that path is confirmed to
   continue normally. Candidates worth ruling in or out once logging exists: the abandoned
   transcription worker in the Edge Cases section below, a blocking `afplay`, or a serial read
   with no data. This issue is the clearest argument for `3a` shipping before anything else in
   Phase 3.

---

## Behaviors

### Rule: Narly signals that it is ready before it starts listening

```scenario
Scenario: The cue plays before listening begins
  Given an attendee has dropped a coin
  When Narly prepares to hear their question
  Then a chime plays and finishes
  And only then does Narly begin listening
  And the lights glow while it listens
```

*Field-verified 2026-09-22:* the chime is audible in a quiet room, and attendees learned to
treat it as their cue to speak. In a busy room it is marginal — people crane toward the cabinet
to catch it. Its audibility is therefore not the limiting factor; its **timing** is, per Open
Issue 4.

### Rule: A question Narly hears is the question the fortune answers

```scenario
Scenario: A clearly spoken question is used
  Given an attendee asks "Will I find treasure today?"
  And Narly hears it clearly
  When the fortune is generated
  Then it is generated from "Will I find treasure today?"
```

### Rule: When Narly hears nothing usable, it asks itself a question instead

```scenario
Scenario: Silence is replaced with Narly's own question
  Given an attendee drops a coin and says nothing
  When Narly gives up listening
  Then the fortune-generation sound plays as normal
  And it proceeds using the question "What is my fortune for today?"
  And the attendee still receives a printed fortune
  And nothing on the ticket indicates the question was substituted
```

*Field-verified 2026-09-22:* this path does not hang. The generation cue sounds and a generic
fortune prints, which is what made the failure invisible rather than merely unreported.

```scenario
Scenario: An unintelligible answer is replaced the same way
  Given an attendee speaks but Narly cannot make out the words
  When Narly gives up on the recording
  Then it proceeds using the question "What is my fortune for today?"
  And the attendee receives a fortune indistinguishable from a heard one
```

### Rule: Listening ends on its own without the attendee doing anything

```scenario
Scenario: An attendee who never speaks is not waited on forever
  Given an attendee drops a coin and stays silent
  When 10 seconds pass with no speech
  Then Narly stops listening
```

```scenario
Scenario: A long-winded question is cut off
  Given an attendee begins speaking
  When they have been speaking for 8 seconds
  Then Narly stops listening and works with what it has
```

```scenario
Scenario: A pause mid-question does not end the recording
  Given an attendee says "Will I find treasure" and pauses to think
  When the pause lasts less than 1.5 seconds
  Then Narly keeps listening for the rest of the question
```

### Rule: A question can be lost to timing as well as to noise

```scenario
Scenario: An attendee speaks the moment the chime ends
  Given an attendee has learned to speak as soon as the chime finishes
  When they begin their question immediately
  Then the opening of their question falls in the gap before Narly starts listening
  And that part of what they said is never recorded
```

```scenario
Scenario: A question is spoken clearly but the room is loud
  Given an attendee waits for the right moment and speaks clearly
  And the room behind them is noisy
  When Narly transcribes what it recorded
  Then the question may still come back unintelligible
  And no amount of waiting or repeating by the attendee changes that
```

### Rule: Every way of failing to hear looks the same to the attendee

```scenario
Scenario: Two different failures produce the same experience
  Given one attendee is misheard because the room is loud
  And another attendee is not heard because the microphone is unplugged
  When each of them collects their fortune
  Then neither is told anything went wrong
  And the two failures are indistinguishable from each other
```

---

## Edge Cases

### Rule: Narly recovers from every capture failure rather than stopping

```scenario
Scenario: The transcription service cannot be reached
  Given the booth has lost its internet connection
  When an attendee asks a question
  Then Narly does not crash
  And the fortune run continues with the substituted question
```

```scenario
Scenario: The microphone is unavailable
  Given the microphone has been unplugged from the laptop
  When an attendee drops a coin and speaks
  Then Narly does not crash
  And the fortune run continues with the substituted question
```

```scenario
Scenario: The whole listening stage overruns
  Given transcription hangs rather than returning
  When 25 seconds have passed since listening began
  Then Narly abandons the attempt
  And the fortune run continues with the substituted question
```

> needs human input: whether abandoning at 25 seconds leaves the microphone usable for the next
> attendee, or whether the abandoned attempt keeps holding the device. The code starts the work
> on a background worker and stops waiting for it, but does not stop the work itself. The owner
> reports occasional unexplained hangs (Open Issue 5); whether they are this is unconfirmed, and
> guessing either way would be inventing a cause. Logging should settle it.

---

## Test Coverage

| Scenario | Test File | Status |
|----------|-----------|--------|
| The cue plays before listening begins | — | Not covered |
| A clearly spoken question is used | — | Not covered (code-derived) |
| Silence is replaced with Narly's own question | — | Not covered |
| An unintelligible answer is replaced the same way | — | Not covered (code-derived) |
| An attendee who never speaks is not waited on forever | — | Not covered (code-derived) |
| A long-winded question is cut off | — | Not covered (code-derived) |
| A pause mid-question does not end the recording | — | Not covered (code-derived) |
| An attendee speaks the moment the chime ends | — | Not covered (code-derived) |
| A question is spoken clearly but the room is loud | — | Not covered (code-derived) |
| Two different failures produce the same experience | — | Not covered (code-derived) |
| The transcription service cannot be reached | — | Not covered (code-derived) |
| The microphone is unavailable | — | Not covered (code-derived) |
| The whole listening stage overruns | — | Not covered (code-derived) |

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
