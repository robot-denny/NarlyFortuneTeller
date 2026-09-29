# Measuring how well Narly hears

This page lets you measure how often Narly hears an attendee's question correctly, using the Fifine
AM8 microphone at the booth. You run one session with volunteers, score it with two commands, and
paste the scores into the results at the bottom. Later, you can score any change to Narly against
the same recordings without asking the volunteers back.

It is written for the owner and the volunteers. You don't need to know Python. Type each command
exactly as shown, from the Narly folder (the one that holds `serial_trigger.py`). If Narly isn't set
up on this computer yet, do the one-time setup in [testing.md](testing.md) first.

The session uses three files:

- `docs/baseline-script.csv` is the script: 60 numbered questions, one per coin.
- `clips/session.log` is Narly's log of the session. Narly makes it.
- `clips/<id>.wav` is what Narly heard on each coin, saved as a sound file named after the
  question's number. These are the "clips".

## Setup checklist

Do these before the volunteers arrive. Write down each value you note: it goes into the results
entry, so the next session can copy the same setup.

- [ ] **Mount the AM8 on its stand, up by Narly.** Aim it at where an attendee's mouth will be.
- [ ] **Note the mic's height, distance, and angle.** Height from the floor, distance from the
      attendee's spot, and which way it points.
- [ ] **Note the gain knob's position** on the AM8. Gain is how much the mic boosts your voice.
- [ ] **Set the Mac's input to the AM8.** Open **System Settings → Sound → Input** and choose the
      AM8. Narly listens on whatever input is chosen here. A session recorded on the laptop's own
      mic gives the wrong numbers, and nothing warns you.
- [ ] **Check the level meter.** On the same settings page, speak from arm's length and watch the
      input level meter move.
- [ ] **Pick a crowd-noise recording and a phone volume.** Note the recording's name and the
      volume. Use the same ones every session, so the conversation scores stay comparable.
- [ ] **Check the `.env` file is there.** Each coin makes a real OpenAI fortune, so Narly needs the
      key. Without it, Narly still listens and logs what it heard, but every ticket is the
      fallback slip.
- [ ] **Empty the `clips` folder.** Clips left from an earlier test are scored as if they came from
      this session, whenever their number matches a script question. The log is kept there too,
      and Narly adds to it rather than starting over. Move the old folder aside, putting today's
      date in its new name:

      ```bash
      mv clips clips-old-YYYY-MM-DD
      ```

      If you see `No such file or directory`, there was no `clips` folder yet. That's fine. Narly
      makes it when the session starts.

## Running the session

Run this in a plain terminal you type into yourself. Don't run it through Claude or any tool that
starts programs without a keyboard attached. Narly waits for you to press Enter, and without a
keyboard it quits early.

```bash
.venv/bin/python serial_trigger.py --mode simulate --dry-run --save-clips clips --log-file clips/session.log
```

Here is what each part does:

- `--mode simulate` means Enter stands in for the coin, so the Arduino isn't needed.
- `--dry-run` shows the ticket on screen instead of printing it.
- `--save-clips clips` saves what Narly heard on each coin into the `clips` folder.
- `--log-file clips/session.log` keeps the log in a file, which is what gets scored.

### Each question

Work through the script in id order: 1 to 20 quiet, 21 to 40 with conversation, 41 to 60 leaning
in.

1. At `Press ENTER for coin →`, type the question's id from the script, for example `7`.
2. Press **Enter**.
3. Wait for the chime to end. Then the volunteer asks the question.
4. Wait for the ticket to appear and the prompt to come back.

Always type the id. A blank line doesn't follow the script. It numbers clips 1, 2, 3 on its own,
so the scores would line up with the wrong questions. An id with a space or a slash is refused too:
Narly uses its own next number and logs a WARNING naming what you typed.

**Volunteers say the question exactly as written, and don't say "Narly" first.** The scoring checks
word for word. Google also hears "Narly" as "gnarly", so a perfectly heard question would still
score as a miss. This rule is only for the session. Attendees can say anything.

**If a volunteer goes off script**, type the same id again at the next prompt and ask again. Only
the last try counts.

### Running it alone: the 20-question session

With no volunteers, run a shorter session yourself: ids **1 to 10** in quiet, then ids **21 to 30**
with the crowd noise playing. Skip the leaning block. Type each id as usual. The scoring counts
only the questions you asked, and the replay's `No clip:` line lists the other 40, which is
expected. Use ids 21 to 30 for the noise block, not 11 to 20: the script marks each id's condition,
so 11 to 20 would be scored as quiet.

Judge the chime yourself from the attendee's spot. In the results entry, write "solo, owner's
voice" under **Anything unusual**. You know the questions, so the score runs higher than
strangers would get. It still compares fairly with a later solo session, such as one on the Pi.

### The three conditions

- **Quiet (ids 1 to 20).** No crowd noise. The volunteer stands where an attendee would.
- **Conversation (ids 21 to 40).** Play the crowd-noise recording from the phone, behind the booth,
  at the volume you noted.
- **Leaning (ids 41 to 60).** Keep the crowd noise playing. The volunteer leans toward the mic, as
  attendees do. Leaning in may score worse, not better. A mic this close can boom or distort, and
  that is a finding, not a fault.

### Two things to watch during the conversation block

- **The chime.** A volunteer standing at the attendee's spot says whether they heard the chime
  clearly, faintly, or not at all. Note the verdict.
- **Early wake-ups.** Watch for Narly deciding someone has started speaking before the volunteer
  opens their mouth. The crowd noise can do that. Note roughly how often you saw it.

When the last question is done, press **Ctrl+C** to stop Narly.

## Scoring

Score the session straight from its log:

```bash
.venv/bin/python baseline.py live clips/session.log docs/baseline-script.csv --clips clips
```

Then send the same clips through Google's recognizer again and score that:

```bash
.venv/bin/python baseline.py replay clips docs/baseline-script.csv
```

The replay needs the internet, because Google does the listening. It makes no fortune and costs
nothing.

Each command prints a short block that starts with `### Live` or `### Replay`. Copy the whole block
into your results entry below. The block gives:

- **Heard correctly**, overall and for each condition. "Correctly" means the words match the script
  exactly, ignoring capitals and punctuation.
- **Unreachable**: coins where Google couldn't be reached. These are counted on their own line and
  left out of every percentage, since they say nothing about hearing.
- **Hit the 8-second cap**: questions where Narly was still listening when its time limit ran out.
- **Misses by kind**, and a table of every miss. `misheard` means Narly heard words, but not the
  script's words. The other kinds are the outcomes listed in [testing.md](testing.md#the-six-outcomes).

The replay also ends with a `No clip:` line. It lists questions that have no saved clip, usually
because Narly heard nothing live. They are left out of the replay's percentages.

## Re-running later

After any change to how Narly hears, run the replay command again, with the same `clips` folder and
the same script. The questions and the recordings stay the same, so the new score compares directly
with the old one.

A replayed clip only tests the recognizer. The clip already stops where Narly stopped listening on
the day, so it can't test a new way of deciding when someone has finished speaking.

When Narly moves to the Raspberry Pi, copy the `clips` folder to the Pi and replay it there.

The clips are the volunteers' voices, and the log holds their words. Neither is ever committed.
Git ignores the whole `clips` folder, so they can't be added by accident.

## Results

Add each session as a new entry at the end of this section. Copy the template, fill it in, and
paste the two blocks the scoring commands printed.

### Template

```markdown
### YYYY-MM-DD, <where the session ran>

**Setup**

- Mic: Fifine AM8. Height: … Distance from the attendee's spot: … Angle: …
- Gain knob: …
- Mac input checked as the AM8: yes / no
- Crowd noise: <recording name>, phone volume …
- Volunteers: <how many>

**Conditions**

- Quiet: ids 1–20
- Conversation: ids 21–40
- Leaning: ids 41–60
- Anything unusual: …

**Live**

<paste the ### Live block here>

**Replay**

<paste the ### Replay block here, including the No clip line>

**Chime over conversation:** clearly / faintly / not at all

**Early wake-ups noted:** …
```

<!-- New entries go below this line, oldest first. -->

### 2026-09-28, home office, the laptop

**Setup**

- Mic: Fifine AM8. Front right of the cabinet, against the front and side lip, tilted slightly
  toward the centre. Aimed at the face of someone standing about 2.5 ft back, facing the cabinet,
  upright after leaning in to drop the coin. Distance to the speaker: about shoulder-to-wrist.
  Top edge about 8 in below the speaker's face, angled up toward it.
- Gain knob: about 1 o'clock. Monitor/headphone knob: 12 o'clock (doesn't affect the recording).
- Mac input checked as the AM8: yes
- Crowd noise: Spotify, "Essential Sound Effects: People Talking in Background (v2) Crowd Group
  People Talk Talking Chat Chatting Mingle Mingling Lobby". iPhone volume 70%, through a Bose
  speaker 3.5 ft behind the speaker and 2.5 ft to their left, at torso height (on the desk).
- Volunteers: none; the owner alone.

**Conditions**

- Quiet: ids 1–10
- Conversation: ids 21–30 (same 10 questions as 1–10)
- Leaning: not run
- Anything unusual: solo, owner's voice (knew the questions)

**Live**

- Heard correctly overall: 60% (12 of 20)
- quiet: 70% (7 of 10)
- conversation: 50% (5 of 10)
- Unreachable (recognizer_error, left out of the shares): 0
- Hit the 8-second cap: 0
- Misses by kind: misheard 8

| id | kind | asked | heard |
| --- | --- | --- | --- |
| 4 | misheard | Is love waiting around the corner? | is love waiting around the |
| 6 | misheard | Will I travel somewhere warm soon? | I travel somewhere warm soon |
| 7 | misheard | What does the ocean hold for me? | what does the ocean hold for |
| 21 | misheard | Will I find treasure today? | find treasure today |
| 24 | misheard | Is love waiting around the corner? | waiting around the corner |
| 26 | misheard | Will I travel somewhere warm soon? | will I travel somewhere warm |
| 27 | misheard | What does the ocean hold for me? | what does the ocean |
| 29 | misheard | Should I learn to play guitar? | I learn to play guitar |

**Replay**

- Heard correctly overall: 60% (12 of 20)
- quiet: 70% (7 of 10)
- conversation: 50% (5 of 10)
- Unreachable (recognizer_error, left out of the shares): 0
- Hit the 8-second cap: 0
- Misses by kind: misheard 8

| id | kind | asked | heard |
| --- | --- | --- | --- |
| 4 | misheard | Is love waiting around the corner? | is love waiting around the |
| 6 | misheard | Will I travel somewhere warm soon? | I travel somewhere warm soon |
| 7 | misheard | What does the ocean hold for me? | what does the ocean hold for |
| 21 | misheard | Will I find treasure today? | find treasure today |
| 24 | misheard | Is love waiting around the corner? | waiting around the corner |
| 26 | misheard | Will I travel somewhere warm soon? | will I travel somewhere warm |
| 27 | misheard | What does the ocean hold for me? | what does the ocean |
| 29 | misheard | Should I learn to play guitar? | I learn to play guitar |

No clip: 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60

**Chime over conversation:** audible

**Early wake-ups noted:** none noticed. The owner didn't notice any cut-offs in the moment either,
though the log shows eight.

**What the misses show:** all eight are clipped questions, not misheard ones. Google got every
word it was given right. Four lost the last word or two (ids 4, 7, 26, 27), four lost the first
word (ids 6, 21, 24, 29). The replay matches the live score miss for miss, so a different
recognizer wouldn't change these; when Narly starts and stops recording would. The end cut-offs
are what the held `dynamic_energy_threshold` fix targets.

### 2026-09-28, home office, the laptop, wake level held

The same setup, noise, and 20 questions as the entry above, run the same evening. One change:
Narly holds the room's wake level while listening instead of raising it mid-question
(`dynamic_energy_threshold = False` after calibration).

**Setup and conditions:** as above. Mac input checked as the AM8: yes.

- Anything unusual: two ids were mistyped at the prompt (`77` for 7, `2424` for 24). Both were
  heard correctly. The scores below come from a copy of the log with those two ids fixed; the
  original log is kept beside it.

**Live**

- Heard correctly overall: 95% (19 of 20)
- quiet: 100% (10 of 10)
- conversation: 90% (9 of 10)
- Unreachable (recognizer_error, left out of the shares): 0
- Hit the 8-second cap: 0
- Misses by kind: misheard 1

| id | kind | asked | heard |
| --- | --- | --- | --- |
| 26 | misheard | Will I travel somewhere warm soon? | will I travel somewhere warm |

**Replay**

- Heard correctly overall: 95% (19 of 20)
- quiet: 100% (10 of 10)
- conversation: 90% (9 of 10)
- Unreachable (recognizer_error, left out of the shares): 0
- Hit the 8-second cap: 0
- Misses by kind: misheard 1

| id | kind | asked | heard |
| --- | --- | --- | --- |
| 26 | misheard | Will I travel somewhere warm soon? | will I travel somewhere warm |

No clip: 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60

**Against the entry above:** 60% → 95% overall, quiet 70% → 100%, conversation 50% → 90%. The four
end cut-offs fell to one (id 26). The four first-word losses went too, for a reason not yet
understood. No question hit the 8-second cap, so holding the level didn't make Narly wait on the
crowd noise. One run each, one voice, and the second time through the same questions, so treat
the size of the jump with some care.
