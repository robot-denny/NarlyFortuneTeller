# Spec for live-baseline

> This spec captures initial requirements and design rationale. For **current system
> behavior**, see the doc named on the **Work type** line below — a new feature doc for a new
> capability, an existing feature doc for a change, or a `docs/` runbook for a fix.

branch: feature/live-baseline
design reference (if any): none
discovery: `_work/shipped/capture-measure-and-fix/discovery.md` → *Direction*, item 2 (no
discovery of its own; this increment was scoped there)

**Work type**: change-to audio-capture
**Feature doc**: audio-capture

## Summary

Narly's long-run target is **at least 60% of attendees heard correctly** in a room with
background conversation. Increment 1 built the instrument: every fortune now logs what was
heard, or which way hearing failed. This increment takes the first real reading, and sets up a
way to take the **same** reading again after every later change. That way each iteration can
be compared with the one before.

**The goal is a baseline and a way to track it, not hitting 60% now.** The biggest gains are
expected from the better mic, an updated AI model, and the Pi port. Past events went well despite
the audio problems. The next event starts **Wednesday 2026-09-30**, and some retesting will be
needed after the Pi port anyway. So this increment is **deliberately lean**: whenever there is a
choice, it takes the simpler path.

**The microphone is settled: the Fifine AM8**, a USB dynamic mic that picks up mainly from the
front. The owner has decided to keep it, and the Samson Q20 is out of scope. This increment
mounts it where it will live at the booth.

One measuring session does double duty. Volunteers ask scripted questions at the booth, in three
room conditions. Narly scores each one live from its log, and it also saves what it heard as a
clip. Those clips become the **replay set**: a fixed collection that any later version of Narly
can be scored against, in minutes, with no volunteers and no fortune cost.

## Functional Requirements

**The microphone, mounted**

- The AM8 is mounted on a stand in its booth position: up by Narly, facing where an attendee's
  mouth will be. The position, the distance to the attendee, and the gain setting are written down
  so the setup can be reproduced.
- The setup notes include checking that the computer's input is set to the AM8 before a session
  starts. This is a checklist line, not a software feature, which is the lean choice.

**One measuring session**

- The session runs in simulate mode, with Enter standing in for the coin. The Arduino is rewired
  in parallel, and is not needed to measure hearing.
- Volunteers read from a numbered script of questions: 20 questions in each of three conditions.
  - **Quiet room.**
  - **Conversation behind**: a recording of crowd noise, played from a phone or speaker behind the
    booth, so the noise is the same every session.
  - **Leaning in**: the volunteer leans toward the mic as attendees do.
- During the session, Narly **saves the audio it heard on each coin as a clip**, linked to the
  script's question number. Nothing extra is recorded, and there is no separate recording pass.
- Clips stay on the laptop, in a folder git ignores. They are volunteers' voices, and the repo is
  public, so they are never pushed. This is also the simplest place to keep them. They are copied
  to the Pi when the Pi port needs them.

**Scoring, one rule for everything**

- **Heard correctly** means the words heard match the script's question once capital letters and
  punctuation are ignored. Anything else is a miss. The rule is mechanical on purpose: a later
  iteration's score must be measured exactly the same way, and a judgement call would drift.
- A score reports:
  - the share heard correctly, **overall** (the target is overall)
  - the same share for each condition
  - how many misses fell into each of the five failure kinds
  - how many recordings ran to the 8-second cap
- Every miss is listed with the question asked and what was heard, so a near miss ("should I bake
  the job") can be seen, even though it scores as a miss.
- An unreachable recognizer is reported on its own line, and is not counted against hearing.

**Two scores from the one session**

- **Live score**: from that session's log, against the script.
- **Replay score**: the saved clips, replayed through the real speech recognizer, with **no
  fortune generated or paid for**, scored by the same rule. This is the number every later
  iteration re-runs.

**The baseline, on the record**

- Both scores are written into a dated results file in the repo. It holds numbers and missed
  words, not audio. It also records the setup, the conditions, and the mic, so later results can
  be added underneath and compared line by line.

**Two quick checks from the same session**

- **The chime.** With conversation playing, a volunteer at the attendee's position says whether
  they heard the readiness chime clearly, faintly, or not at all (Open Issue 7).
- **Early wake-ups.** Whether conversation woke Narly before a volunteer spoke is noted by
  watching, not measured. Voice detection in a later increment is the real fix for this.

**Preserved**

- What an attendee sees and hears is unchanged: the same chime, lights, ticket, and fallback slip.
- Saving clips happens only when asked for. A normal run at the event saves no audio.
- Offline runs (`--offline`) still make no network calls and cost nothing.

## Design Reference (only if one exists)

None. No visual surface changes. The physical change is the mic's mount and position.

## Possible Edge Cases

- **The input isn't the AM8.** A session recorded on the laptop mic would give the wrong numbers
  without anyone noticing. The setup checklist guards against this.
- **Leaning in too close.** A dynamic mic boosts bass and can distort at a few inches, so leaning
  in may score worse, not better. That is a finding, not a fault.
- **A saved clip is only what Narly heard.** It starts when listening starts and stops where
  Narly stopped listening. So the replay set can measure a new recognizer, but not a new way of
  deciding when a question has ended. The endpointing-and-recognition increment will need longer,
  raw recordings for that part. This is accepted, because it's the price of recording in a single
  pass.
- **Conversation wakes Narly before the volunteer speaks.** The saved clip then holds crowd noise
  and part of the question. It scores as a miss, which is exactly what an attendee would get.
- **A volunteer goes off script** ("Will I find treasure?" when the script says "…today?"). It
  scores as a miss. The volunteer can re-ask, and the script number is not reused.
- **The recognizer is unreachable** during the session or a replay. Those runs are reported
  separately and excluded from the hearing score.
- **A near-perfect transcript** ("will i find treasure to day") scores as a miss under the
  mechanical rule. Accepted: the rule must stay the same between iterations, and the miss list
  shows how near it was.

## Acceptance Criteria

1. The AM8 is mounted in its booth position, and the setup notes (position, distance, gain,
   input check) are written down.
2. A measuring session of 20 scripted questions in each of the three conditions has been run in
   simulate mode.
3. During that session, Narly saved each coin's heard audio as a clip linked to its script
   number. A normal run saves nothing.
4. The saved clips can be replayed through the real speech recognizer with no fortune generated
   or paid for.
5. Both the live score and the replay score report the overall and per-condition share heard
   correctly under the one mechanical rule, the misses by failure kind, the 8-second-cap count,
   and each miss's question and heard words.
6. A dated results file records both scores, the setup, and the conditions, in a form later
   results can be added to.
7. The chime's audibility over conversation has a recorded verdict.
8. Re-running the replay set on the Pi is part of the Pi-port increment's scope on the roadmap.

## Scenarios (Draft)

Draft BDD scenarios derived from the acceptance criteria using Example Mapping. Each Rule maps
to an acceptance criterion; scenarios use concrete examples. These get verified and refined
after implementation — the feature doc holds the verified version.

### Rule: The booth microphone setup can be reproduced

```scenario
Scenario: Setting up from the written notes
  Given the notes say the mic stands 30 cm above the counter, angled at the attendee's mouth, with its gain at the marked level, and the computer's input set to the AM8
  When the operator sets up at the event
  Then the mic ends up in the same position, with the same gain, as its only input
```

### Rule: A measuring session saves what Narly heard, question by question

```scenario
Scenario: A scripted question becomes a clip
  Given a measuring session is running in the "conversation behind" condition
  And script question 27 is "Should I take the job?"
  When a volunteer drops a coin and asks it
  Then Narly saves what it heard as a clip for question 27
  And the log records what it heard, as on any run
```

```scenario
Scenario: A normal run saves nothing
  Given Narly is running at the event
  When an attendee asks "Will I find treasure today?"
  Then no audio is saved
```

### Rule: Heard correctly means the same words, ignoring capitals and punctuation

```scenario
Scenario: A match despite capitals and punctuation
  Given the script question is "Will I find treasure today?"
  When Narly hears "will I find treasure today"
  Then it counts as heard correctly
```

```scenario
Scenario: A near miss is still a miss
  Given the script question is "Should I take the job?"
  When Narly hears "should I bake the job"
  Then it counts as a miss
  And the miss list shows "Should I take the job?" next to "should I bake the job"
```

### Rule: A score reports overall, per condition, and by failure kind

```scenario
Scenario: Scoring a session
  Given 60 scripted questions, 20 in each condition
  And 42 were heard correctly: 18 quiet, 11 conversation behind, 13 leaning in
  When the session is scored
  Then it reports 70% heard correctly overall
  And 90% quiet, 55% conversation behind, and 65% leaning in
  And how many of the 18 misses were silence, not understood, a microphone fault, or an overrun
  And how many recordings ran to the 8-second cap
```

```scenario
Scenario: A network outage does not count against hearing
  Given the recognizer was unreachable for 4 of the 60 questions
  When the session is scored
  Then those 4 are reported as unreachable
  And the share heard correctly is out of the other 56
```

### Rule: The replay set gives the same kind of score, at no fortune cost

```scenario
Scenario: Replaying the set
  Given 60 saved clips from the measuring session
  When the operator replays them through the real recognizer
  Then each is scored against its script question by the same rule
  And the replay score is reported in the same form as the live score
  And no fortune was generated or paid for
```

### Rule: The baseline is written down so the next iteration can compare

```scenario
Scenario: The first entry in the results file
  Given the live score was 70% overall and the replay score was 72% overall
  When the baseline is recorded
  Then the results file has a dated entry with both scores, the setup, and the conditions
  And a later entry can be added beneath it and compared line by line
```

### Rule: The chime's audibility has a verdict

```scenario
Scenario: Checking the chime over crowd noise
  Given crowd noise is playing behind the booth at the session's usual level
  When a volunteer standing where an attendee stands drops a coin
  Then they report hearing the chime clearly, faintly, or not at all
  And that verdict is recorded in the results file
```

## Open Questions

Settled with the owner (2026-09-28), kept here so the reasoning survives:

- **Arduino:** not needed. Simulate mode is used, and the owner rewires the Arduino in parallel.
- **The 60% target:** applies **overall**. Per-condition shares are reported but are not targets.
- **Clips per condition:** 20 is plenty.
- **Where clips live:** the path of least resistance: a git-ignored folder on the laptop,
  copied to the Pi when needed.
- **Pi retest:** yes. The Pi-port increment re-runs the replay set on the Pi.
- **The event:** starts Wednesday 2026-09-30. Past events went well despite the audio problems.
  The aim is visible improvement and a way to track it, so time is spent on the leanest path, not
  on hitting a number.

Decided while writing this spec, on the lean principle. Revisit any of them if they're wrong:

- **"Conversation behind" is a recorded crowd played from a phone or speaker**, not live people.
  It's repeatable and needs nobody extra.
- **"Heard correctly" is a mechanical match** (capital letters and punctuation ignored), so every
  iteration scores the same way. Near misses show in the miss list.
- **Clips are saved by Narly during the live session**, not recorded separately. One pass of
  volunteers gives both scores. The cost: the replay set can't measure a new way of detecting
  when a question ends (see Edge Cases).
- **The mic check is a checklist line**, not a feature that logs the input device.
- **Early wake-ups are noted by watching**, not measured.

Still open:

- **The AM8's power draw on the Pi.** It is USB-powered, and its RGB light draws power. This goes
  to the Pi port's power budget.

## Testing Guidelines

Meaningful tests for the cases below, without going too heavy:

- Saving clips happens only when asked for. A normal run saves nothing.
- A saved clip is linked to its script question number.
- Replaying clips through the recognizer makes no fortune call. Prove it with the fortune
  stand-in, as Increment 1's offline tests do.
- The "heard correctly" rule, pinned by examples: a match despite capitals and punctuation, a
  one-word difference that misses, and a blank transcript that misses.
- Scoring a small known set gives the right overall and per-condition shares, the right counts
  by failure kind, and the right 8-second-cap count. An unreachable recognizer is excluded from
  the hearing share.
- The measuring session itself is manual: the owner and volunteers at the booth, recorded in the
  results file with its date, setup, and conditions.
