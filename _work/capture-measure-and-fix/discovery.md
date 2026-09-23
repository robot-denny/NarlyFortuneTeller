# Discovery: Hearing Attendees Reliably, and the Path to the Pi

_Discovery input for `/spec` — produced by `/explore` on 2026-09-22. Scope: heavyweight._

Reconciles `docs/v3-upgrade-plan.md` (the September audit) against the owner's stated
priorities, two events' field experience, and the two feature docs written since. Supersedes the
increment boundary in `_work/phase-3ab-logging-watchdog/spec.md` (feature branch, unmerged).

## Problem framing

- **Who is affected.** Festival attendees, who drop a custom sea-net token and ask Narly a
  question aloud; and the operator, who cannot see failures as they happen. When it works,
  people are delighted — that experience is the thing to preserve.
- **Observed pain** (two events, laptop-based, October 2025 and February 2026):
  - In a quiet room, transcription is accurate "more often than not." With conversation in the
    room — even quiet conversation — success falls to **30–40%**.
  - Attendees did not know when to start speaking. A chime was added; it is hard to hear in
    noise, and it sounds *before* listening actually begins.
  - Narly often could not tell when the attendee had finished; in noise, listening ran to the
    8-second cap. Background words did **not** pollute transcripts.
  - Attendees leaned in and cupped their hands over the mic and were *still* often misheard.
  - Most failures printed a **generic fortune**; a minority answered a specific but wrong
    question. Occasional hangs of unknown cause.
- **Anticipated pain** (from reading code; not yet seen on the Mac): the double serial open and
  Uno DTR reset (audit 0a) — Linux behaviour that becomes real on the Pi.
- **Code findings that explain the observations** (recorded in `_features/audio-capture.md`,
  Open Issues 1–5): a ~2.8s dead window between chime and `listen()`; `energy_threshold` set to
  1100 against a library default of 300, with both adaptation mechanisms disabled and a
  backwards comment; `TIMEOUT_RECORDING` inert; all five capture failures collapsing into one
  silent default-question substitution. The owner's tuning of the threshold ran 800–1400 and
  never reached the sensitive range, so the threshold hypothesis is **untested, not refuted**.
- **The problem in one sentence.** In a room with conversation, attendees are heard correctly
  about a third of the time, because the machine starts listening too late, needs too loud a
  voice to wake up, cannot find the end of a question in noise, and records nothing about which
  of those went wrong.

## Outcomes sought

- **≥ 60% of attendees heard and answered correctly** in a room that is not loud but has
  background conversation. Whole pipeline, though everything after capture is already trusted.
- That number **measured**, not felt — the current 30–40% is an impression, and every previous
  tuning effort was judged the same way.
- Narly running on the **Raspberry Pi 4 for the next event**, which is in the near future.
- The delight preserved: no robustness change may make a working fortune worse.

## Options considered

**Capture — hearing the attendee**

- **Directional mic (cardioid/supercardioid), mounted up by Narly.** The AC-404 is a boundary
  mic facing the room, below the attendee's mouth. A directional mic on-axis rejects the
  conversation behind. *Near-term:* biggest lever on the noise case, zero code. *Long-term:*
  permanent mount up top; stand beside the cabinet as a test rig. *Worse at:* nothing for
  on-axis, close speech — attendees who leaned in still failed, so this is necessary, not
  sufficient. Mic arrives in 1–2 days.
- **Sequencing fix — cue and `listen()` start in the same instant.** Removes the dead window
  that trained attendees to speak too early. *Worse at:* nothing; pure correctness. Coupled to
  replacing `afplay`, which dies silently on Linux.
- **Threshold to library default (~300) with adaptation re-enabled.** Cheap; never tested.
  *Worse at:* may trigger on background speech in a noisy room — no single fixed value works
  there, which is the argument for VAD.
- **Silero VAD for endpointing.** Right fix for the observed run-to-cap failure; energy-based
  endpointing cannot find a pause in a room with conversation. *Worse at:* a dependency change
  bundled with dropping `SpeechRecognition`, so a second step, not a first.
- **Paid cloud STT (gpt-4o-transcribe / Deepgram) replacing the free Google endpoint.**
  Addresses the *minority* failure (specific-but-wrong). *Worse at:* irrelevant until audio is
  actually captured; ranked below the four above. Same key already in `.env`; audio already
  leaves the machine, so no new privacy posture.
- **TTS voice prompt as readiness cue.** Most legible cue possible. *Worse at:* latency, and
  Phase 2e work. Held in reserve until the existing cues are tested with correct timing.

**Architecture**

- **Fake hardware layer, scoped.** Coin and printer are already faked by `--mode simulate
  --dry-run`; LEDs degrade to no-op. Missing: a fake **mic** that replays WAV fixtures, and
  fakes for STT and the LLM. *Near-term:* makes capture experiments reproducible and lets
  remote testers run the app with no hardware and no API cost. *Worse at:* a typed-question
  fake tests nothing in capture — it must replay real clips recorded at the booth.
- **Single serial owner (audit 0a).** Deferred from "first" to "part of the Pi increment": the
  DTR reset is a Linux defect and the Pi is now near-term.
- **Event loop + state machine (audit Phase 1).** Deferred. Does not move the 60% number;
  unblocks Phase 4 sensors, which come last.
- **Custom watchdog (V2 3b). Rejected.** The next event is on the Pi; systemd does this with
  zero code. The 3a+3b spec narrows to instrumentation.
- **Fortune bank (audit 1c).** Deferred until logging exists — it hides the one diagnostic tell
  the operator currently has.

## Trade-offs & second-order effects

- **Measurement before tuning is the spine.** All five capture failures print the same ticket.
  Any fix chosen before they are logged distinctly is a guess about which cause dominates.
- **The hardware gap sets the order for free.** Mic is days away; Arduino is dismantled. Every
  software-only change — logging, fake mic, sequencing, threshold, playback — fits the gap, so
  the first live session with the new mic produces numbers on day one.
- **Journald conflict.** The audit says make journald volatile to protect the SD card; the point
  of logging is post-event review. Volatile logs vanish at the first power cut. Needs persistent
  size-capped logs or off-device shipping. Unresolved.
- **Dropping `SpeechRecognition` forces the STT decision** — it is both the trigger and the
  recognizer. Fix threshold and timing inside it first; swap the stack as a later step.
- **A USB condenser on the Pi shares the bus** with the Arduino and printer (audit 3f). A
  brownout presents as random disconnects indistinguishable from software bugs.
- **Deferring the state machine keeps Phase 4 blocked.** Accepted; sensors are last by
  priority.

## Direction

Chosen: a sequence of four increments, then the deferred work. Verifiable on the Mac through
the first; the Pi enters at the third.

1. **`capture-measure-and-fix`** *(now, during the hardware gap — this increment).* Log the five
   capture failures distinctly and what was heard; fake mic with WAV replay plus STT/LLM fakes;
   cue and `listen()` in the same instant; threshold to library default with adaptation on;
   cross-platform playback replacing `afplay`. Absorbs V2 3a. Drops 3b.
2. **Live baseline** *(mic arrives, Arduino rewired).* New directional mic on a stand; record
   fixture clips across quiet/conversation/leaning-in; first measured success rate.
3. **Pi port** *(critical path to the event).* Persistent journald, systemd unit, single serial
   owner (0a), stable device names, `deploy/`. Absorbs V2 3c–3f and audit 3a–3f.
4. **Endpointing and recognition** *(measured against the fixtures).* Silero VAD; cloud STT with
   local fallback. Audit 2a–2b.
5. **Later.** Fortune bank; TTS prompt; state machine; sensors and sketch rewrite (audit 4–5).

Rationale: it puts the cheapest, most-indicated fixes first, makes every later change
measurable, uses the hardware gap rather than waiting on it, and reaches the Pi before the
event without carrying a watchdog that would be thrown away.

## Open questions for /spec

- **When exactly is the next event?** Bounds how much of increments 2 and 4 lands before 3.
- **Journald: persistent with a size cap, or volatile plus off-device shipping?** Owner's call.
- **How long are recorded attendee questions kept, and are logs cleared between events?**
- **Playback library** — `pygame.mixer` vs `sounddevice`/`simpleaudio`. Device contention with
  capture on the Pi is the deciding concern.
- **Which mic, and USB-powered or via interface?** Power budget on the Pi.
- **Does threshold ~300 with adaptation trigger on background speech?** The fixtures answer this.
- **What is causing the hangs?** Abandoned transcription worker, blocking `afplay`, or a stalled
  serial read — the new logging should discriminate. Not to be guessed.
- **Increment 1 is broad.** `/spec` may want to split fakes from fixes; the argument for
  keeping them together is that the fakes are what make the fixes testable in the gap.
