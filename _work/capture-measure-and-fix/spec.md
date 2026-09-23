# Spec for capture-measure-and-fix

> This spec captures initial requirements and design rationale. For **current system
> behavior**, see the doc named on the **Work type** line below — a new feature doc for a new
> capability, an existing feature doc for a change, or a `docs/` runbook for a fix.

branch: feature/capture-measure-and-fix
design reference (if any): none
discovery: `_work/capture-measure-and-fix/discovery.md` — framing, options, and open questions
are taken from there and not re-argued here.

**Work type**: change-to audio-capture
**Feature doc**: audio-capture

## Summary

Narly hears attendees correctly about a third of the time in a room with background
conversation. The discovery traced that to four causes in how Narly listens — it starts
listening ~2.8 seconds after the cue, it needs a raised voice to wake up, it cannot find the end
of a question in noise, and every one of its failures prints the same generic fortune so nothing
records which cause struck. It also found that the sound cues vanish silently on Linux, which is
where the next event runs.

This increment does the software-only part of the fix, sized to the current hardware gap — the
directional mic is days away and the Arduino is dismantled. It makes capture **observable**, so
the 60% target can be measured rather than felt; makes it **reproducible**, so the same recorded
question can be replayed through Narly on any machine with no hardware and no API spend; and
lands the two cheapest, best-indicated **fixes**: the cue and listening starting together, and a
wake-up threshold at the library's default with adaptation on. Endpointing and the recogniser are
the next increment, measured against the fixtures this one makes possible.

The custom watchdog from the earlier `phase-3ab-logging-watchdog` spec is dropped: the next event
runs on the Pi, where systemd restarts the process with zero code. The logging half of that spec
lives here. Its `unattended-operation` feature doc is superseded — the read-back rules fold into
`audio-capture`; the restart rules move to the Pi increment.

## Functional Requirements

**Observability — the operator can tell what happened**

- Every fortune run records what Narly heard the attendee ask, verbatim as transcribed.
- The five ways hearing can fail — nothing heard, heard but not understood, the recogniser
  unreachable, the microphone unavailable, the whole stage overrunning — are recorded as five
  distinguishable outcomes, never as one.
- When Narly substitutes its own question for one it did not hear, that substitution is recorded
  as such, so a generic fortune can be traced to its cause afterwards.
- Records carry a timestamp and a severity, and an operator can count outcomes across an event.
- The operator's live view on the laptop behaves as it does today.

**Reproducibility — Narly can run with nothing plugged in**

- A tester can run a complete fortune, coin to ticket, with no microphone, no Arduino, and no
  printer attached, and without spending anything on the transcription or fortune services.
- The tester supplies the attendee's question either as a recorded clip or as typed text.
- The same recorded clip produces the same recorded outcome every time it is replayed.
- Someone who has never touched the hardware can run this on their own machine.

**Fixes — the two the evidence indicates**

- Narly begins listening in the same instant the readiness cue sounds. There is no interval
  after the cue during which speech is lost.
- Narly wakes to an ordinary speaking voice at arm's length, and adapts its sense of "quiet" to
  the room rather than holding a fixed value. The library's own default is the starting point.
- The readiness cue and the thinking cue play on Linux as well as macOS, and play in-process so
  their timing relative to listening is under Narly's control.

**Preserved**

- Everything the attendee sees and hears otherwise stays as it is — the same cues, the same LED
  states, the same 32-character ticket, the same fallback slip.

## Design Reference (only if one exists)

None. No visual or physical surface changes.

## Possible Edge Cases

- A recorded clip is shorter than the listening window, or contains only room noise. Replay must
  end cleanly, and the outcome recorded must be the same one a live attendee would produce.
- With a sensitive threshold and adaptation on, background conversation may itself wake Narly
  before the attendee speaks. The discovery flagged this as the argument for VAD; this increment
  must record it when it happens rather than hide it.
- The replacement playback library is missing or has no output device — as on a remote tester's
  machine, or a headless Pi with no speaker. Cues must degrade quietly, as they do today, and the
  degradation must be recorded rather than swallowed.
- The `sfx/` files are absent on a tester's machine. Same: degrade, and record.
- A typed question is supplied where a clip was expected, or a clip where text was expected.
- Power is cut mid-write; the last record is truncated. Every complete record before it must be
  intact.
- A one-word utterance transcribes as nothing. That is "heard but not understood",
  and must be recorded as such rather than as silence.
- The transcribed question contains a stranger's personal details. Recording it is the decision
  made in discovery; the log's location and lifetime are open questions below.

## Acceptance Criteria

1. After any fortune run, an operator can read from the log what Narly heard, or which of the
   five failures occurred, and whether the question was substituted.
2. Across a day's log, the operator can count how many questions failed and how many fell into
   each of the five kinds.
3. Warnings and errors are distinguishable from ordinary progress; every record is timestamped.
4. A tester with no hardware runs a full fortune from a recorded clip, and from typed text, at no
   cost, and the run completes.
5. Replaying the same clip twice yields two identical outcomes in the log.
6. There is no measurable interval between the readiness cue and the start of listening.
7. Narly wakes to a normal speaking voice at arm's length without the attendee raising it.
8. Both cues play on a Linux machine.
9. An attendee's experience of a heard fortune is indistinguishable from today's.

## Scenarios (Draft)

Draft BDD scenarios derived from the acceptance criteria using Example Mapping. Each Rule maps
to an acceptance criterion; scenarios use concrete examples. These get verified and refined
after implementation — the feature doc holds the verified version.

### Rule: The operator can read back what Narly heard, or why it did not

```scenario
Scenario: A heard question is on the record
  Given an attendee asked "Will I find treasure today?" at 2:15pm
  And Narly heard it correctly
  When the operator reads the log that evening
  Then the 2:15pm run shows the question "Will I find treasure today?"
```

```scenario
Scenario: A substituted question is marked as substituted
  Given an attendee dropped a coin at 3:40pm and said nothing
  And Narly printed a fortune for "What is my fortune for today?"
  When the operator reads the log
  Then the 3:40pm run shows that nothing was heard
  And it shows the question was substituted, not asked
```

### Rule: The five ways of failing are told apart

```scenario
Scenario: Silence and an unintelligible answer are different records
  Given one attendee dropped a coin and never spoke
  And another attendee mumbled a single word
  When the operator reads the log
  Then the first run is recorded as "nothing heard"
  And the second is recorded as "heard but not understood"
  And the two records are not the same
```

```scenario
Scenario: Counting an event's failures by kind
  Given Narly served 60 attendees across a day
  And 18 of them were not heard correctly
  When the operator reviews the log
  Then they can count 18 failures
  And they can see how many were silence, how many were not understood, how many were the
    recogniser unreachable, how many were a microphone fault, and how many overran
```

### Rule: A tester needs no hardware and spends nothing

```scenario
Scenario: A remote tester runs a fortune from a recorded clip
  Given a tester on their own laptop with no mic, Arduino, or printer attached
  And a recorded clip of someone asking "Should I take the job?"
  When they run a fortune using that clip
  Then the run completes and produces a ticket on screen
  And the log shows the question "Should I take the job?"
  And no call was made to the paid transcription or fortune services
```

```scenario
Scenario: A tester runs a fortune from typed text
  Given a tester with no hardware attached
  When they run a fortune with the typed question "Should I take the job?"
  Then the run completes with a ticket on screen
  And the log shows the question as typed
```

### Rule: The same clip gives the same answer every time

```scenario
Scenario: Replaying a clip is repeatable
  Given a recorded clip of an attendee asking a question in a noisy room
  When the tester replays it twice
  Then both runs record the same outcome
  And both runs record the same heard text, or the same kind of failure
```

### Rule: Listening begins the instant the cue sounds

```scenario
Scenario: An attendee who speaks on the cue is heard from the first word
  Given an attendee has learned to speak the moment the chime sounds
  When they begin "Will I find treasure today?" as the chime starts
  Then the whole question is recorded, including "Will"
```

### Rule: Narly wakes to an ordinary voice

```scenario
Scenario: A normal speaking voice is enough
  Given an attendee standing at arm's length from the cabinet
  When they ask their question at conversational volume, without leaning in
  Then Narly begins recording
  And the question is heard
```

```scenario
Scenario: Narly adjusts to the room rather than a fixed setting
  Given the room was quiet in the morning and has conversation in it by afternoon
  When an attendee asks a question in the afternoon at the same volume as the morning
  Then Narly still begins recording
```

### Rule: The cues play on the Pi

```scenario
Scenario: Cues on a Linux machine
  Given Narly is running on a Linux machine with a speaker attached
  When an attendee drops a coin
  Then the readiness chime plays
  And the thinking cue plays once the question is captured
```

### Rule: The attendee's experience of a heard fortune is unchanged

```scenario
Scenario: A successful fortune looks and sounds the same
  Given all of the above is in place
  When an attendee drops a coin, waits for the chime, and asks "What is my fortune?"
  Then they hear the same chime and thinking cue as before
  And they see the same LED states as before
  And they receive a printed ticket of the same width and layout
```

## Open Questions

Carried from discovery, with two added while writing scenarios.

- **When exactly is the next event?** Bounds how much of this and the next increment land before
  the Pi port. --assume we can complete all of this and the next increment. 
- **Where does the log live and how long is it kept?** Attendee questions are personal. Cleared
  between events? Journald on the Pi is persistent by decision; the laptop path is undecided.
- **Which in-process playback library?** Device contention with capture on the Pi decides it;
  the discovery names `pygame.mixer`, `sounddevice`, and `simpleaudio` as candidates.
- **Does the default threshold with adaptation wake on background conversation?** The fixtures
  answer this. If yes, the "wakes to an ordinary voice" rule is in tension with the noise case,
  and that tension is what the next increment's VAD resolves.
- **What is causing the occasional hangs?** Not to be guessed. This increment's log should let
  the next one say.
- **Should fakes and fixes be one increment or two?** The argument for one: the fakes are what
  make the fixes checkable during the hardware gap. `/plan` may still split the steps.
- *(New)* **How is "no measurable interval" verified without hardware?** A replayed clip that
  starts speaking at time zero proves the first word is captured; that is the fixture to record.
- *(New)* **Does the fixture set exist yet?** No clips have been recorded. The live-baseline
  increment records them; until then, this increment's replay is tested with clips recorded at
  a desk, which proves the mechanism but not the noise case.

## Testing Guidelines

The project has no test framework today — see `.agents/config/stack.md` → *Tests*. **This
increment is the one that changes that.** Once a fortune can run with no hardware and no API
spend, an automated check becomes possible for the first time, and the plan should introduce a
test runner rather than adding more manual steps. Per `tdd-principles`, assert observable
outcomes — what the log records, what the ticket says — never how capture is wired internally.

Meaningful checks, without going too heavy:

- Each of the five failure kinds, provoked through the fakes, produces its own distinct record —
  five records, five different kinds, none collapsing into another.
- A substituted question is recorded as substituted, and the recorded text matches the persona's
  default.
- A recorded clip with speech from time zero yields a transcript that begins with the first word.
- The same clip replayed twice yields identical records.
- Typed-text and clip-based runs both complete and both log.
- Playback with no output device degrades and records the degradation, and does not stop the run.
- `.venv/bin/python -m compileall -q *.py` still exits clean, and `--list-personas` still prints
  three personas.
- A manual pass with the real mic once it arrives, at conversational volume, arm's length, no
  leaning in — the check that the threshold change did what the evidence predicted.
- A manual pass on a Linux machine confirming both cues are audible.
