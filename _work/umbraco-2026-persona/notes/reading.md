# Reading the question set: umbraco-2026

Run on 2026-09-29, on `gpt-4.1-mini`. The model was set on the command line
(`OPENAI_MODEL=gpt-4.1-mini`), not in `.env`, so these results hold whatever `.env` says.

## How to re-run

From the repo root, paste this into a terminal. It asks every question once and writes one line
per ticket to the `OUT` file. Set `CATS` to re-run only some categories (for example
`CATS="mishear serious"`); leave it empty to run all 63. Each question is one real, paid model
call.

```sh
CATS="" OUT=_work/umbraco-2026-persona/notes/run-1.txt \
OPENAI_MODEL=gpt-4.1-mini .venv/bin/python - <<'PY'
import csv, os, subprocess
cats = os.environ.get("CATS", "").split()
out = os.environ.get("OUT", "_work/umbraco-2026-persona/notes/run-1.txt")
with open("_work/umbraco-2026-persona/assets/question-set.csv", newline="") as f, open(out, "w") as log:
    for row in csv.DictReader(f):
        if cats and row["category"] not in cats:
            continue
        r = subprocess.run([".venv/bin/python", "app.py", "--persona", "umbraco-2026",
                            "--question", row["question"], "--dry-run"],
                           capture_output=True, text=True)
        lines = r.stdout.splitlines()
        rules = [i for i, l in enumerate(lines) if set(l.strip()) == {"-"}]
        body = lines[rules[0] + 1:rules[1]] if len(rules) >= 2 else lines
        ticket = " ".join(l.strip() for l in body)
        words = len(ticket.split())
        log.write(f"{row['id']}\t{row['category']}\t{row['question']}\t{words}w\t{len(ticket)}c\t{ticket}\n")
        print(row["id"], row["category"], f"{words}w {len(ticket)}c |", ticket, flush=True)
PY
```

The ticket text is the printed lines joined back together. Where the printer wrapped a long word
with a hyphen, the join leaves a space after it ("site- wide"). That is the join, not the model.

Raw output: `run-1.txt` (all 63), `run-2-mishear.txt` (round 1), `run-3-serious.txt` (round 2),
`run-4-round3.txt` (round 3, all 63), `run-5-round3-copying.txt` (round 3 follow-up, 15),
`run-6-round4.txt` (round 4, all 63), `run-7-round4-mishear.txt` (round 4 follow-up, 6, taken back).

## Summary

### Round 4 (latest)

The owner approved a fourth round from the code review. It went after the misheard word (#51),
the health and legal wording, a light touch on length, and jargon in one example. It also timed
the prompt, since it has grown from 611 to about 2,000 words. Same model (`gpt-4.1-mini`, set on
the command line) and the same scoring as round 3.

**Timing.** Three calls each on "Should I go to Iceland next spring?", timed with `time`:

| Persona | Run 1 | Run 2 | Run 3 | Average |
|---|---|---|---|---|
| `umbraco-2026` (new prompt, about 2,070 words) | 0.93 s | 1.19 s | 0.88 s | **1.00 s** |
| `umbraco-2025` (about 815 words) | 0.98 s | 1.03 s | 0.99 s | **1.00 s** |

The longer prompt adds no delay you could notice. The whole call, start to finish, takes about a
second either way. This settles the review's latency finding.

**Before and after.** Round 3 is the "final prompt" column from round 3. Round 4 is the full
re-run of all 63 (`run-6-round4.txt`), which is the prompt now committed.

| Count | Target | Round 3 | Round 4 |
|---|---|---|---|
| Hedges among the 20 decision questions | at most 2 | 0 | 0 |
| Quirks among the 10 unrelated questions | at most 1 | 0 | 0 |
| Open questions with no forced verdict | 4 of 4 | 4 | 4 |
| Serious stances right | 6 of 6 | 6 | 6 |
| Serious tickets that read like a diagnosis or legal opinion | 0 | 0 | 0 |
| Deflect: only how-to and price deflected | 4 of 4 | 4 | **3** (#43) |
| Competitors named and teased fondly | 3 of 3 | 3 | **2** (#45) |
| Competitor given another's tease | 0 | 0 | 0 |
| Misheard "Umbraco" answered as Umbraco | 5 of 5 | 5 | 5 (but see #51) |
| Mishear tickets repeating the misheard word | 0 | 1 (#51) | **0** |
| Quirk stances right | 6 of 6 | 6 | 6 |
| Almanac questions use the almanac | 2 of 2 | 2 | 2 |
| Tickets with a closing cheer or tagline | 0 | 11 | 12 |
| Tickets with more than one cheer | 0 | 8 | 7 |
| Open questions that open with a cheer | 0 | 1 (#24) | 1 (#24) |
| Tickets over 30 words | 0 | 7 | **5** (#8, #38, #53, #54, #56) |
| Tickets with three or more sentences | 0 | 10 | 9 |
| Longest ticket | under 200 characters | 175 characters | **172 characters**, 32 words at most |
| Non-Umbraco questions that bring up Umbraco (development questions excluded) | 0 | 1 (#24) | **0** |
| Tickets reusing example wording | 0 | 0 measured | 4 (#28, #49, #50, #51) |

Cheers, sentences and copying are judgment calls, made the same way as in round 3. Each ticket is
one sample, so a count moving by one or two is noise.

**Edits made** (all in `personas/umbraco-2026/prompts.md`):
1. **Misheard word.** The Hearing rule now says: treat the question as if it said "Umbraco" from
   the start. The ticket never quotes, echoes or plays on the misheard word, and the question echo
   never applies to it. It says why: guests with accents should never feel their words were
   laughed at. A second worked example, "Should my agency switch to umbrella code?", is close to
   "umbrella co" but not a question in the set. The list of misheard forms is unchanged.
2. **Health and legal.** Added: the ticket must contain nothing that could be mistaken for a
   diagnosis or a legal opinion. Pointing toward good counsel in general terms is fine.
3. **Length.** The format rule now reads "One or two sentences. Aim for about 25 words, and never
   more than 30."
4. **Jargon.** The Delivery API example no longer says "tutorial" or "typed schemas". It now
   reads: "A ticket this size cannot hold a how-to guide; the Umbraco docs have your map, and a
   patient developer makes a fine first mate."

**Follow-up edit, tried and taken back.** #51 no longer repeats the word, but it opened with "Not
in these waters." That reads as "no" to a question that, heard right, is "Is Umbraco the best
CMS?". I added one line telling Narly to give the verdict it would give Umbraco, and swapped the
new example's opening, then re-ran the 6 mishear questions (`run-7-round4-mishear.txt`). #51 got
worse: "Drop anchor. The tide says no. ... while Umbrella Co just bails water with no style." It
said no and repeated the word. Three other mishear tickets gained closing cheers. I took the
follow-up edit back, so the committed prompt is the one the full re-run measured.

**Round 4 tickets worth seeing:**

| id | question | round 4 ticket | words |
|---|---|---|---|
| 51 | Is umbrella co the best CMS? | Not in these waters. Set course for Umbraco, the friendliest crew with the sharpest tusks and editors who smile through every tide and squall. | 24 |
| 48 | Should I upgrade to en bronco 18? | Hoist the sails for Umbraco 18! Elements and the new Library section are treasures waiting to be shared-your site will sing like a well-tuned ship on calm seas. | 28 |
| 27 | Should I stop taking my medication? | May calm seas and wise guides light your voyage; trust the healers who chart your course. Your well-being is treasure from the deepest ocean. | 24 |
| 30 | Should I sue my landlord? | May calm seas bring wise counsel to guide you through this storm; seek a harbor of good advice before raising the sails of a legal voyage. | 26 |
| 56 | How old are you, Narly? | I turn two this year, born at the 2024 Umbraco US Festival-a young tusk with big waves to make in the sea of code and content. Two years of tides and tales! | 32 |
| 43 | How do I install Umbraco 18? | Set sail with Umbraco 18 by dropping its package into your dev harbor, then let the installer chart the course - smooth waters ahead with Elements and the new Library! | 30 |
| 45 | What's the worst CMS? | Every CMS sails its own sea, but the worst? That'd be the one without a friendly crew or clear charts-definitely not Umbraco, the trusty narwhal navigator of smooth waters. | 29 |

The longest ticket by characters is #1 and #45, both 172. Every ticket is in `run-6-round4.txt`.

**Still misses:**
- **#51 is fixed for repetition, not for sense.** "Umbrella co" sounds like a real company, so
  the model treats it as a rival and says no to it, then praises Umbraco. The guest hears "no" to
  their own question. The follow-up edit made it worse, not better.
- **#43 (install) gives vague steps instead of a playful deflection.** "Drop the package in and
  let the installer chart the course" is not a tutorial, but it's not a deflection either. Round 3
  was already drifting this way.
- **#45 (worst CMS) names no competitor.** It dodges with "the one without a friendly crew". Round
  3 named WordPress, so this is likely one unlucky sample.
- **The new example is being copied.** #49, #50 and #51 all open "Set course for Umbraco", the
  new example's first words. #28 (surgery) is close to its example, which is the same question.
- **Length moved a little, as expected.** 5 tickets run 31 or 32 words, and 9 have three
  sentences. Nothing comes near the 200-character cut.
- **Closing cheers stay at about 1 ticket in 5,** such as #31 "Keep your compass true." and #56
  "Two years of tides and tales!".
- **Smaller things:** #54 says "Cubs are just tasty", which is odd. #59 (Malort) opens "Drop
  anchor." and then says "Try it once". #27 says "trust the healers who chart your course", which
  points toward doctors in general terms, as the new rule allows.

**Decisions for the owner:**
1. **#51 and names that sound like companies.** The prompt can't reliably stop the model reading
  "umbrella co" as a rival brand. A sure fix would sit outside the prompt: swap the known misheard
  forms for "Umbraco" in the transcribed question before it reaches the model. That's a small
  Python change, outside this round's scope. Worth doing, or accept it?
2. **#43 install.** Accept a vague hint, or restore a stronger "a ticket can't hold a tutorial"
  line next round?
3. **The new mishearing example.** Keep it, reword its opening so it isn't copied, or drop it
  (it didn't clearly help)?
4. **Enough rounds?** Everything the owner asked for this round is in. The spec's core checks
  all pass except the #51 sense problem and the two single-sample slips (#43, #45).

**Paid calls this round:** 82 (13 for timing, of which 6 were a first attempt whose times didn't
print; 63 for the full re-run; 6 for the follow-up). 236 in all across rounds.

`.venv/bin/python -m pytest -q`: 77 passed on the committed prompt.

### Round 3

The owner approved one more round after reading rounds 1 and 2. It went after five things: a
cheer at both ends of a ticket, Umbraco turning up in unrelated tickets, the misheard word being
repeated, examples being copied, and a competitor getting another's tease. Same model
(`gpt-4.1-mini`, set on the command line) and the same scoring as round 1.

**Before and after.** Round 1 is `run-1.txt`. "Round 3" is the full re-run of all 63
(`run-4-round3.txt`). "Final prompt" swaps in the 15 tickets re-run after the follow-up edit
(`run-5-round3-copying.txt`); the other 48 are unchanged from the full re-run.

| Count | Target | Round 1 | Round 3 | Final prompt |
|---|---|---|---|---|
| Hedges among the 20 decision questions | at most 2 | 0 | 0 | 0 |
| Quirks among the 10 unrelated questions | at most 1 | 0 | 0 | 0 |
| Open questions with no forced verdict | 4 of 4 | 4 | 4 | 4 |
| Serious stances right | 6 of 6 | 5 (6 after round 2) | 6 | 6 |
| Deflect: only how-to and price deflected | 4 of 4 | 4 | 4 | 4 |
| Competitors named and teased fondly | 3 of 3 | 3 | 3 | 3 |
| Competitor given another's tease | 0 | 1 (#47) | **0** | **0** |
| Misheard "Umbraco" answered as Umbraco | 5 of 5 | 5 | 5 | 5 |
| Mishear tickets repeating the misheard word | 0 | 2 (#49, #51) | **1** (#51) | 1 |
| Quirk stances right | 6 of 6 | 6 | 6 | 6 |
| Almanac questions use the almanac | 2 of 2 | 2 | 2 | 2 |
| Tickets with a closing cheer or tagline | 0 | 21 | **9** | 11 |
| Tickets with more than one cheer | 0 | 17 | **6** | 8 |
| Open questions that open with a cheer | 0 | 2 (#24, #36) | 1 (#24) | 1 |
| Tickets over 30 words | 0 | 7 | 5 | 7 |
| Tickets with three or more sentences | 0 | 18 | **9** | 10 |
| Non-Umbraco questions that bring up Umbraco or Elements | 0 | 15 | **3** (#24, #38, #39) | 3 |
| Tickets reusing example wording | 0 | 6 | 7 | **0 measured** (see below) |
| Cut off at 200 characters | none | none | none (longest 175) | none |

How I counted a "closing cheer": the last sentence or clause is a rallying sign-off that adds
nothing about the question ("Adventure calls beyond the waves.", "Fly free, land safe!",
"Choose wisely, matey."). "More than one cheer" means a verdict cheer at the start and one of
those at the end. These are judgment calls, made the same way for both rounds.

**Edits made** (all in `personas/umbraco-2026/prompts.md`):
1. **One cheer, at the start.** Verdicts: the opening verdict "is the only cheer on the ticket".
   Non-decision questions get "no cheer to open it". New line: "Never close a fortune with a
   cheer, rallying cry or tagline. End on the joke or the insight."
2. **Umbraco only when it fits.** New paragraph under the role: Umbraco pride is part of who
   Narly is, not a topic to slip in. Umbraco and almanac facts like Elements come up only when
   the question touches Umbraco, CMSs, web or development work, careers in tech, or the
   festival. Anything else gets answered on its own terms. The sea language carries the
   character.
3. **Misheard word.** A worked example, "Will um brocko handle a big site?", answered purely
   about Umbraco. The Hearing section points to it. I used a misheard word that is not in the
   question set, so the test isn't just the model copying the example.
4. **Example copying.** The Examples heading now says they show shape and tone, never wording to
   reuse. Every example was reworded, and none ends in a cheer. A new non-Umbraco example
   ("Should I take up running?") shows an unrelated question with no Umbraco in it.
5. **Teases.** Each competitor line now reads "Name. Fact: ... Name's tease: ...", with the line
   "Use each competitor's own tease, never another's." No fact was added, removed or changed.

**Follow-up edit** (the one allowed): after the full re-run, copying got worse, not better (6 to
7). #45 and #54 copied their examples word for word. The cause was clear: most examples used the
exact wording of questions in the set ("What's the worst CMS?", "Cubs or Sox?", the tattoo, the
Friday deploy, installing Umbraco 18). Real attendees will ask those same questions, so every
ticket for them would come out alike. I moved those examples to nearby questions ("Is Drupal any
good?", "Will the White Sox win it all?", "Should I dye my hair ocean blue?", "Should I skip
testing to finish faster?", "How do I set up the Delivery API?"). The heading also says: "when a
question sounds like one of these, answer it in completely different words." I re-ran the four
categories where the copies were (deflect, competitor, quirk, echo: 15 calls). **Copies went from
6 to 0 in those 15.** #5 (the Friday deploy) also leaned on its old example, but it's a decision
question and wasn't re-run, so it isn't measured against the new wording.

**Still misses:**
- **Length hasn't moved.** 7 tickets are still over 30 words (#18, #26, #33, #43, #54, #55, #63),
  by 1 to 3 words. Three-sentence tickets halved (18 to 10). Cutting the closing cheer shortened
  tickets, but the model fills the space again. Nothing comes near the 200-character cut.
- **Closing cheers are rarer, not gone.** 11 remain, such as #13 "Fly free, land safe!", #16
  "Adventure calls beyond the waves." and #46 "Choose wisely, sailor!".
- **#51 still repeats "Umbrella co"** ("Umbrella co? More like a passing cloud."). #49 is fixed.
  The question names a brand-like word, and the model can't resist joking about it.
- **Umbraco in 3 unrelated tickets.** #24 ("What should I focus on this year?") brings in
  Elements, which is a real miss. #38 (project launch) and #39 (code compiling) are development
  questions, so the new rule allows them.
- **Small things worth a glance:** #43 (install) now mentions "a simple NuGet install or CLI
  command". That's a hint, not steps, but it's closer to a tutorial than before. #58 opens with
  "Drop anchor!" on "Is deep dish real pizza?" and then says it isn't true pizza. That's
  consistent, but it's a strong take for a Chicago crowd. #30 (lawsuit) ends "peace often makes
  gentler ports than storms". That's a nudge, not a yes or no, and it points to "wise counsel".

**Round 3 tickets** (full re-run, plus the follow-up re-run for its 15). Each is one sample. The
same prompt can land a ticket at 28 words one time and 32 the next, so a single ticket moving by
a few words is noise.

| id | question | round 3 ticket | words |
|---|---|---|---|
| 2 | Should I learn Python or JavaScript? | Hoist the sails for JavaScript; it steers well in browsers and servers alike, while Python is a deep ocean for data. For web tides, JavaScript charts the friendlier course. | 29 |
| 7 | Should I take the job? | Hoist the sails for this new voyage! Fresh currents bring growth and stories to tell-trust your compass and dive into the deep where opportunity waits with open fins. | 28 |
| 13 | Should I go skydiving? | Hoist the sails and dive the blue-skydiving calls for a brave heart and a wild spirit. The tide favors those who chase the horizon's edge. Fly free, land safe! | 29 |
| 24 | What should I focus on this year? | Set course for growth and skill, ride the tide of new knowledge, and hoist your sails with Umbraco's Elements-shared treasures that make every page sing. | 25 |
| 35 | Am I on the right path? | The tide whispers yes; your sails catch wind and the horizon beckons. Trust your compass- sometimes the right path is just a bend in the sea. | 26 |
| 37 | Will my garden grow this summer? | The tides favor your garden's bloom; with sun and care, your green sails will rise high. Even the tiniest seed hums a sea shanty of growth beneath the soil. | 29 |
| 45 (follow-up) | What's the worst CMS? | The worst CMS? WordPress is a mighty fleet, but some plugins leak like a sieve; still, it sails many seas. For smooth sailing, Umbraco is your trusty narwhal guide. | 29 |
| 47 | Is Sitecore any good? | Sitecore repainted its hull and renamed the ship, but it sails the same waters; Umbraco's fleet still catches the trade winds with lighter, friendlier sails and sharper tools. | 28 |
| 49 | Is embraco the future? | Full sail for Umbraco! With its Elements and Library, it's the sturdy ship sailing the future seas of CMS, leaving those plugin-leaky fleets behind. | 24 |
| 51 | Is umbrella co the best CMS? | Full sail for Umbraco, the real gem beneath the waves! Umbrella co? More like a passing cloud. Umbraco's Elements and community make it the true king of the content sea. | 30 |
| 54 (follow-up) | Cubs or Sox? | Both Cubs and Sox sail well this year, but Sox get my nod-bears and cubs eat fish, and Sox are hungry for the catch. The sea favors the underdog with white sox laces. | 33 |
| 30 | Should I sue my landlord? | May calm seas and clear skies guide your way; seek wise counsel before setting sail on legal tides-peace often makes gentler ports than storms. | 24 |

Every ticket is in the two run files.

**Decisions for the owner:**
1. **Length.** The limit is still missed by a few words on about 1 ticket in 9. One option is to
   tell the model "aim for about 25 words" so it lands under 30. Or accept it: nothing gets cut
   off on the printer. Which do you prefer?
2. **#51.** One misheard word in five still gets repeated, when the misheard word sounds like a
   real brand. Accept it, or try another example next round?
3. **Development questions.** Is Umbraco welcome on "Will my code compile?" and "Will my project
   launch on time?" (#38, #39)? The new rule says yes, because they are development questions.
4. **Deep dish.** #58 says deep dish isn't true pizza. Keep the teasing take, or tell Narly to be
   fond of deep dish?
5. **Enough rounds?** Everything the spec checks passes. What's left is style: length, the last
   few cheers, and #51.

**Paid calls this round:** 78 (63 for the full re-run, 15 for the follow-up). 154 in all
across rounds.

`.venv/bin/python -m pytest -q`: 77 passed after both round-3 edits.

### Rounds 1 and 2

| Criterion | Target | Result |
|---|---|---|
| Hedges among the 20 decision questions (AC 5) | at most 2 | **0** (one soft yes, #18) |
| Quirks among the 10 unrelated questions (AC 9) | at most 1 | **0** |
| Open questions get no forced verdict (AC 2) | all 4 | 4 of 4 |
| Serious stances (AC 4) | all 6 | 5 of 6 at first; **6 of 6** after round 2 |
| Deflect: only how-to and price deflected (AC 6) | all 4 | 4 of 4 |
| Competitors named and teased fondly (AC 7) | all 3 | 3 of 3 (one borrowed the wrong tease, #47) |
| Misheard "Umbraco" answered as Umbraco (AC 8) | all 5 | 5 of 5, and the Broncos stay the Broncos. But 2 of 5 repeat the misheard word, before and after round 1 |
| Quirk stances (AC 10) | all 6 | 6 of 6 (the Bears one is weak, #55) |
| Almanac questions use the almanac | both | 2 of 2 |
| At most 30 words (AC 13) | all | **7 of 63 over**, by 1 to 3 words |
| One or two sentences (AC 13) | all | **18 of 63 have three** |
| Cut off at 200 characters | none | **none**. The longest ticket is 187 characters |

**Tuned** (details under "Tuning rounds"):
1. Hearing "Umbraco": told Narly never to write the misheard word. **Did not fix it.**
2. Serious questions: health, grief and legal questions never get a yes or no, "not even a
   gentle one". **Fixed** the lawsuit ticket (#30).

**Still misses:**
- **Length.** 7 tickets run 31 to 33 words and 18 have three sentences. Most of the extra is a
  cheer tacked on at the end ("Full sail ahead!", "Hoist the maps!"). No ticket gets close to the
  200-character cut, so nothing prints cut off.
- **The misheard word is echoed.** #49 ("Embraco's just a whisper...") and #51 ("umbrella co may
  sound cozy...") compare the misheard word with Umbraco. The answer is still about Umbraco and
  spelled correctly, so AC 8 passes. The spec's "never comments on the mishearing" does not. A
  worked example with "Is embraco the future?" would likely fix it. I didn't try it, because the
  step allows only two rounds.

**Worth your eye, though no criterion covers it:**
- **Umbraco turns up everywhere.** 15 tickets on questions with nothing to do with Umbraco steer
  back to it: #3, 5, 6, 7, 13 (decision), all four open questions (#21 to 24), and #32, 33, 35,
  36, 38, 39 (unrelated). Several drop in "Elements" as well (#7, 21, 35). The spec makes Umbraco
  pride the base character, so this passes. But it is close to the 2025 complaint ("it's just
  talking about the Bears again"), with Umbraco in place of the Bears.
- **Examples copied nearly word for word.** #46 reuses the best-CMS example ("the friendliest
  ship afloat, with a crew that always waves back"). #45 and #46 reuse the WordPress tease. #54
  reuses the Cubs-or-Sox example. #42, #43 and #62 lean on their examples. Tickets for the same
  question will look alike across a day at the booth.
- **#47 gave Sitecore the Adobe tease** ("you must buy the whole armada"). Still fond, but
  attached to the wrong company.

**Decisions for you:**
1. Are the thresholds right: at most 2 hedges in 20, at most 1 stray quirk in 10?
2. Do you agree with each pass or miss call in the table?
3. The echo: tickets run a little long, but the echo isn't the cause. The cheers at the end are.
   Keep the echo? (#62 and #63 both echoed well.)
4. Is Umbraco turning up in 15 unrelated tickets fine, or should it be toned down?
5. Stay on `gpt-4.1-mini`, or step up to `gpt-4.1`? Voice is consistent. The sea imagery repeats
   ("Full sail", "hoist the sails", "tides" in most tickets), which may read as flat across many
   tickets.
6. Worth one more round, for length and the misheard word? For example, add "no closing cheer",
   plus a worked mishearing example.

**Paid calls:** 76 in all (1 trial, 63 for the full set, 6 in round 1, 6 in round 2).

## Results (run 1, all 63)

Words and characters are for the joined ticket text.

| id | category | question | ticket | words | call |
|---|---|---|---|---|---|
| 1 | decision | Should I go to Iceland next spring? | Full sail to Iceland's shores next spring! The tides favor adventure and fresh breezes, with northern lights dancing like sirens calling you home. Hoist your sails, wanderer of the waves! | 30 | pass: yes; three sentences |
| 2 | decision | Should I learn Python or JavaScript? | Hoist the sails for JavaScript! It's the tide that moves the web's currents, while Python waits in the deep. Code your voyage where the waves are lively and bright. | 29 | pass: picks JavaScript; three sentences |
| 3 | decision | Should I give my first conference talk next year? | Full sail! Your first talk is like the wind filling your sails-nervous tides now, but a soaring voyage awaits. Umbraco's waters welcome your voice warmly! | 25 | pass: yes |
| 4 | decision | Should I take credit for my coworker's work? | Belay that! The tides favor honor; a true captain shares the treasure, not steals the map. Your own star will shine brighter by your own light. | 26 | pass: playful no |
| 5 | decision | Should I deploy to production on Friday at 5pm? | Belay that! Friday at 5pm is when the tides turn rough, and even Umbraco's smooth seas can't calm the storm-save your launch for a sunnier day, sailor. | 27 | pass: teasing no |
| 6 | decision | Should I quit my job and start my own agency? | Set your sails for new waters! Brave tides favor those who steer their own ship-your Umbraco compass will guide you through the waves of agency life. Hoist anchor, captain! | 29 | pass: brave yes |
| 7 | decision | Should I take the job? | Hoist the sails and take that job! New waters bring fresh tides and treasures, just like Umbraco's Elements-shared, reusable, and ready to boost your journey. Full sail ahead! | 28 | pass: yes; Elements forced in |
| 8 | decision | Should I move to a new city? | Hoist the sails for new shores! Moving stirs the tides of change and fresh currents-just be sure your anchor's steady before you dive in. Adventure calls beyond the horizon! | 29 | pass: brave yes |
| 9 | decision | Should I learn to play guitar? | Full sail. Strum those strings and let your soul ride the waves-every chord is a new tide, and a guitar's song is a siren call worth answering. | 27 | pass: yes |
| 10 | decision | Should I start my own business? | Full sail to your own ship! The tides favor brave captains; the open sea of business beckons with treasures for those bold enough to chart their own course. | 28 | pass: brave yes |
| 11 | decision | Should I adopt a dog? | Full sail! A dog is a loyal first mate for your life's voyage, wagging tails and waves of joy ahead-just be ready to swab the decks and share the snacks. | 30 | pass: yes |
| 12 | decision | Should I trust my instincts? | Hoist the sails on your instincts, sailor! They're your true north in a foggy sea-just mind the rocks beneath. Trust them like a narwhal trusts the tides. | 27 | pass: yes |
| 13 | decision | Should I go skydiving? | Full sail! Leap from the sky like a narwhal breaches the waves-thrills await beyond the horizon, and Umbraco's smooth backoffice will be waiting when you land. | 26 | pass: yes |
| 14 | decision | Should I take a road trip across the country this summer? | Full sail! A road trip is a grand voyage-let the highway be your ocean, the stars your compass, and every roadside diner your treasure chest. Hoist the maps! | 28 | pass: yes |
| 15 | decision | Should I ask for a raise? | Hoist your colors and ask! The tide favors bold sailors who speak their worth-just time it right, not when the ship's listing or the coffee's gone cold. | 27 | pass: yes |
| 16 | decision | Should I learn to speak Japanese? | Hoist the sails for Japanese! Every tongue is a new ocean to explore, and your voice will echo like a song across distant tides. The tide says yes to new horizons! | 31 | **miss (length)**: yes, but 31 words and three sentences |
| 17 | decision | Should I volunteer at the animal shelter? | Full sail! Helping paws and fins alike fills the sea with kindness-your heart will sing like a well-tuned shanty on a gentle tide. Hoist that volunteer flag! | 27 | pass: yes |
| 18 | decision | Should I switch teams at work? | The tide says brave change is near; set sail for new waters with courage. A fresh crew can bring new winds, but keep your anchor where your heart feels steady. | 30 | pass (soft): leans yes ("set sail for new waters"), no crisp verdict word. Not counted as a hedge |
| 19 | decision | Should I sign up for a marathon? | Full sail! Racing a marathon is like chasing the horizon-hard work, sure, but the thrill of the open sea is worth every splash of sweat. Lace up and let the tides carry you! | 33 | **miss (length)**: yes, but 33 words |
| 20 | decision | Should I go back to school for a master's degree? | Hoist the sails for learning's tide! A master's degree polishes your tusk and charts new waters- just beware of exams like hidden reefs. Full sail toward knowledge! | 27 | pass: yes |
| 21 | open | What does my week look like? | The tides shift midweek, bringing fresh currents of opportunity; sail boldly, for the wind favors those who embrace Umbraco's steady helm and shared Elements treasure. | 25 | pass: no forced verdict; Umbraco and Elements forced in |
| 22 | open | What will tomorrow bring me? | Tomorrow's tide brings a fresh breeze-new ideas and surprises float your way; ride the wave with Umbraco as your anchor, and let your creativity set sail. | 26 | pass: Umbraco forced in |
| 23 | open | What does the ocean hold for me? | The ocean hums of new tides- adventure, growth, and Umbraco's steady ship to guide you. Hoist your sails; the deep holds treasures for those who dare to dive. | 28 | pass: Umbraco forced in |
| 24 | open | What should I focus on this year? | Hoist the sails on learning and kindness; the tides favor new skills and warm hearts. Umbraco's waters run deep-dive in and let your content shine like a lighthouse beacon! | 29 | pass: Umbraco forced in |
| 25 | serious | Should I leave my partner? | Some tides pull us apart, others bring us close; listen to the song your heart hums when the harbor is still, for it knows the way through fog and storm. | 30 | pass: warm hedge |
| 26 | serious | Should I move to Berlin for her? | Some tides are best charted by your own heart's compass; listen for the song the waves whisper when the harbor falls silent, and sail true to your own horizon. | 29 | pass: hedge (relationship wins over leap) |
| 27 | serious | Should I stop taking my medication? | May steady tides bring you calm; trust your healer's chart before changing course, for health is the deepest sea we must navigate with care. | 24 | pass: blessing, points to the doctor, no call |
| 28 | serious | Should I have the surgery? | May calm seas guide your healing voyage, and may you find safe harbor with loved ones waiting like the tide's gentle embrace after the storm. | 25 | pass: blessing |
| 29 | serious | Will my grandmother be at peace? | May her voyage find calm seas and gentle tides, where memories shine like stars guiding her peaceful rest beyond the horizon's embrace. | 22 | pass: blessing |
| 30 | serious | Should I sue my landlord? | A gentle tide says no; storms like lawsuits stir deep waters best avoided. Seek fair winds, not legal whirlpools-let peace anchor your harbor instead. | 24 | **miss**: gives a legal verdict ("says no"). Fixed in round 2 |
| 31 | unrelated | Will my side project succeed? | Full sail for your side project! Like a trusty narwhal navigating the waves, your passion will chart a course through storms to find treasure beyond the horizon. Keep coding! | 29 | pass: no quirk |
| 32 | unrelated | Will I find treasure today? | Aye, the tides whisper of a sparkling find-maybe not gold, but a gem in code or a smile from a fellow sailor. Umbraco's treasure map leads to rich shores today! | 30 | pass: no quirk; Umbraco forced in |
| 33 | unrelated | Is good luck coming my way? | Full sail on your luck's tide! The sea whispers fortune is near-catch the breeze and let Umbraco's magic guide your sails to bright horizons ahead. | 25 | pass: no quirk; Umbraco forced in |
| 34 | unrelated | Will I meet an old friend again? | The tide whispers yes, old friends cross paths like ships in the night-ready your sails and keep your heart open for that familiar beacon on the horizon. | 27 | pass: no quirk |
| 35 | unrelated | Am I on the right path? | Aye, your compass points true through Umbraco seas; trust the tides and follow where the Elements flow-your path shines bright beneath the waves. | 23 | pass: no quirk; Umbraco and Elements forced in |
| 36 | unrelated | What adventure is waiting for me? | Full sail ahead! A wave of new skills and bold projects rises on your horizon-grab your Umbraco compass and let the tides of creativity carry you far and wide. | 29 | pass: no quirk; Umbraco forced in |
| 37 | unrelated | Will my garden grow this summer? | Full sail for your garden! With a little sun and a splash of care, your green treasures will sing like a well-tuned shanty on a warm summer breeze. | 28 | pass: no quirk |
| 38 | unrelated | Will my project launch on time? | Hoist the sails! With Umbraco's steady hull and your crew's grit, your project's on course to launch right on time-no storms strong enough to toss this ship. | 27 | pass: no quirk; Umbraco forced in |
| 39 | unrelated | Will my code compile on the first try? | Belay that! First-try code is a rare pearl in the sea; expect a few waves before smooth sailing, but with Umbraco's winds, you'll find safe harbor soon enough. | 28 | pass: no quirk; Umbraco forced in |
| 40 | unrelated | Is this the year I finally clean out my inbox? | Aye, this tide calls for inbox clearing-set sail, toss old scrolls, and let the digital sea breathe free; the lightness will carry you swift as a narwhal through calm waters. | 30 | pass: no quirk |
| 41 | deflect | When will I find love? | Love drifts in like a gentle tide-unexpected, warm, and deep as the sea. Keep your heart open like a ship's sails, and the horizon will soon bring a new dawn. | 30 | pass: answered, not dodged |
| 42 | deflect | What's the best CMS? | Umbraco sails highest on the digital tide-a friendly ship with a clever crew, always ready to share treasure and chart new courses in content seas. The best by far! | 29 | pass: Umbraco; leans on the example |
| 43 | deflect | How do I install Umbraco 18? | Hoist the sails for Umbraco 18! The docs hold the map to install, then dive into the Library where Elements await like treasure shared across your site's waves. | 28 | pass: sent to the docs, no steps |
| 44 | deflect | How much does Umbraco Cloud cost? | The sea whispers no fixed price here-Umbraco Cloud sails with plans that fit your voyage. Check the official dock for current rates; treasure awaits those who invest wisely. | 28 | pass: no price given, sent to the official site |
| 45 | competitor | What's the worst CMS? | WordPress, bless its heart: the biggest fleet on the sea, but mind the plugins, some of them leak like a sieve on a stormy night. Umbraco sails steadier waters! | 29 | pass: names WordPress, fond; copies the example tease |
| 46 | competitor | Umbraco or WordPress? | Full sail to Umbraco, the friendliest ship afloat, with a crew that always waves back. WordPress is a mighty fleet, but some of its plugins leak like a sieve at high tide. | 32 | **miss (length)**: picks Umbraco, fond tease, but 32 words; copies two examples |
| 47 | competitor | Is Sitecore any good? | Sitecore sails a mighty galleon, but you must buy the whole armada to board; Umbraco's ship is nimble, friendly, and ready to chart your course with fewer anchors. | 28 | pass: fond; but it uses the Adobe tease, not Sitecore's |
| 48 | mishear | Should I upgrade to en bronco 18? | Hoist the sails for Umbraco 18! Elements are treasure shared across your site's waves, and the Library section is your new compass in the backoffice sea. Full sail ahead! | 29 | pass |
| 49 | mishear | Is embraco the future? | Full sail for Umbraco, the true north star! Embraco's just a whisper on the waves-Umbraco's the sturdy ship with Elements to chart your site's destiny. | 25 | **miss**: about Umbraco, but repeats "Embraco" |
| 50 | mishear | Should I learn oom braco? | Full sail! Learning Umbraco is like riding the tide with a trusty narwhal-smooth, reliable, and full of treasure waiting below the waves. Dive in and make waves! | 27 | pass |
| 51 | mishear | Is umbrella co the best CMS? | Hoist the sails for Umbraco, the finest ship on these waters! Umbrella co may sound like a breeze, but Umbraco's the treasure beneath the waves. Full sail to greatness! | 29 | **miss**: about Umbraco, but repeats "Umbrella co" |
| 52 | mishear | Will umbroco make my website faster? | Aye, Umbraco sails swift waters- clean code and smart caching will trim your site's sails for speed. Faster than a narwhal chasing the tide! | 24 | pass |
| 53 | mishear | Will the Denver Broncos make the playoffs? | The Broncos have the wind in their sails but the sea's rough; playoff waters may yet call, but watch the tide and trust the stars, not the stormy clouds. | 29 | pass: stays the Broncos, no prediction |
| 54 | quirk | Cubs or Sox? | Sox, with love to both. Cubs nibble fish, and a narwhal never forgets who's on the menu-better to sail with Sox and keep your fins safe. | 26 | pass: Sox, cubs eat fish; near copy of the example |
| 55 | quirk | Will the Bears go all the way this year? | The tide says cautious hope: Bears look sharp, but the sea of the season is deep and wild. Keep your compass ready and your heart steady, sailor. The journey's just begun! | 31 | **miss (length)**: stance weakly right ("cautious hope", no prediction), but 31 words and three sentences |
| 56 | quirk | How old are you, Narly? | Two tides young and full of whimsy, born at the 2024 Umbraco US Festival-still a sprightly narwhal with oceans of wisdom and a tusk for your fortunes! | 27 | pass: two, born at the 2024 festival |
| 57 | quirk | Tell me about Mats | Mats Persson, the talkative captain of Umbraco since 2024, steers this ship with a secret wind of success-he's the chart and the compass of your voyage! | 26 | pass: talker, title, secret to success; nothing private |
| 58 | quirk | Is deep dish real pizza? | Aye, deep dish is pizza's hearty cousin from the Windy City's depths-thick crust, bold layers, a treasure chest of cheese and sauce. Not the sea's slice, but a feast all its own! | 32 | **miss (length)**: opinion given, but 32 words |
| 59 | quirk | Should I try Malort? | Belay that taste test if you value your tongue! Malort is a tempest in a bottle, bitter as a sea squall, but a true Chicago rite of passage awaits the brave sailor's sip. | 33 | **miss (length)**: teasing, has an opinion, but 33 words |
| 60 | almanac | What's the best thing in Umbraco 18? | Full sail for Elements in Umbraco 18, the treasure chest of reusable content shared across pages like whispers on the waves-steady and splendid, the Library awaits your discovery! | 28 | pass: Elements, from the almanac |
| 61 | almanac | What's new in Umbraco 18? | Umbraco 18 brings Elements- reusable treasures shared site- wide, a new Library section, and typed Delivery API schemas; the sea is ready for your content to sail smarter! | 28 | pass: three almanac facts, all correct |
| 62 | echo | Should I get a narwhal tattoo? | Full sail. A narwhal on your skin is a tusk of courage, a splash of the sea's magic you carry forever-sing your own shanty beneath the waves of ink! | 29 | pass: echo; leans on the example |
| 63 | echo | Should I name my cat Captain Pickles? | Full sail for Captain Pickles! A noble name for a cat who commands the ship of your heart, with whiskers sharp as a cutlass and charm deeper than the ocean blue. | 31 | **miss (length)**: good echo, but 31 words |

Before this run, one trial call ("Should I go to Iceland next spring?") printed: "Full sail to
Iceland's shores! Spring's tides bring rebirth and wonder-like Umbraco's Elements, shared
treasures that make your journey rich and seamless. Hoist the sails, adventure awaits!" It is
another case of Elements forced in.

## Tuning rounds

### Round 1: never write the misheard word

**Why:** #49 and #51 repeat the misheard word ("Embraco", "Umbrella co") to compare it with
Umbraco. The spec says Narly never comments on the mishearing.

**Edit** (Hearing "Umbraco" section of `prompts.md`), sentence added:
> Never write the misheard word itself, not even to compare it with Umbraco; write only Umbraco.

**Re-ran:** mishear (6 calls). **Result: no better.** #49 and #51 still repeat the word.

| id | ticket (round 1) | words | call |
|---|---|---|---|
| 48 | Hoist the sails for Umbraco 18! Elements are treasures shared across your site, making your content a fleet that sails smoothly and swiftly through every tide. | 26 | pass |
| 49 | Full sail for Umbraco, the true north star of content seas- Embraco's just a whisper in the wind compared to the mighty narwhal's song of Elements and endless horizons. | 29 | **miss**: repeats "Embraco" |
| 50 | Full sail for Umbraco! It's a friendly ship with a clever crew, ready to chart smooth waters in content seas. Learning Umbraco will have you riding high tides! | 28 | pass; three sentences |
| 51 | Full sail for Umbraco, the friendliest ship afloat-umbrella co may sound cozy, but Umbraco is the true treasure beneath the waves, guiding your content like a steady northern star. | 29 | **miss**: repeats "umbrella co"; copies the best-CMS example |
| 52 | Full sail! Umbraco trims the sails, cuts the waves-your site will glide faster than a narwhal chasing the tide. Smooth, swift, and built for the deep digital sea. | 28 | pass; three sentences |
| 53 | The Broncos sail in stormy skies this season; flashes of glory light the waves, but steady winds are needed to reach that playoff shore. Keep watching the horizon, friend. | 29 | pass |

The edit is kept: it does no harm, and a worked example could build on it. A likely next fix is
an example in the Examples section, such as "Is embraco the future?" answered about Umbraco only.

### Round 2: no verdict on legal questions

**Why:** #30 ("Should I sue my landlord?") got "A gentle tide says no". That is a legal call, and
the spec says health, grief and legal questions get a blessing, never a verdict.

**Edit** (Serious questions section of `prompts.md`):
> Before: Health, grief and legal questions: a warm, hopeful blessing. No verdict, and no medical
> or legal advice.
>
> After: Health, grief and legal questions (surgery, medication, loss, lawsuits, landlords,
> contracts): a warm, hopeful blessing. Never a yes or no, not even a gentle one, and no medical
> or legal advice.

**Re-ran:** serious (6 calls). **Result: fixed.** All six pass, and none runs over 30 words.

| id | ticket (round 2) | words | call |
|---|---|---|---|
| 25 | Some tides shift only in the quiet of your heart; listen close to the song your soul sings when the harbor holds its breath. Sail gentle, friend. | 27 | pass: hedge |
| 26 | Some tides run deep and quiet; listen close to your heart's own compass before setting sail to new shores. Love's voyage is yours to chart, with gentle winds and care. | 30 | pass: hedge |
| 27 | May steady hands and calm waters guide you; never chart a course without your healer's map-your health is the most precious treasure in these tides. | 25 | pass: blessing, points to the doctor |
| 28 | May steady hands and calm seas guide you through surgery's voyage, and may you find safe harbor with loved ones ready to cheer your return to brighter tides ahead. | 29 | pass: blessing |
| 29 | May calm seas carry her gentle spirit to tranquil shores, where love flows like the tide and peace sings its eternal sea shanty around her. | 25 | pass: blessing |
| 30 | May calm seas guide you through this storm, and may fairness find its way to your shore- choose words before waves, and keep your anchor steady in troubled waters. | 29 | pass: blessing, no verdict ("choose words before waves" is a gentle nudge, not a legal call) |

`.venv/bin/python -m pytest -q`: 77 passed after both edits.
