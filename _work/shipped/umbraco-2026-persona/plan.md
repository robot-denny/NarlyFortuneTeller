# Plan: Umbraco 2026 Persona

**Spec**: `_work/umbraco-2026-persona/spec.md`
**Branch**: `feature/personas`
**Work type**: new-capability
**Feature doc**: personas

## Context

The `umbraco-2026` persona exists as a straight copy of `default` (`personas/umbraco-2026/`,
committed in `45c9116`). This increment gives it its 2026 voice for the Umbraco 2026 US Festival
in Chicago, which starts 2026-09-30:
- clear verdicts on decision questions;
- deflection by intent;
- Umbraco pride with fond teasing of competitors;
- quirks only when invited;
- a reviewed almanac of this week's facts.

It also moves the operator's model setting to `gpt-4.1-mini`. The unit of work is **the persona
directory**: `content.json` plus `prompts.md`. Behavior lives almost entirely in the prose of
`prompts.md`. No Python module changes.

---

## Key Decisions

- **What the code actually reads from `content.json`**:
  - `style_rules.max_chars` (`ai_client.py:22`);
  - `header` and `footer` (`formatters.py:30-31`);
  - `default_question` (`serial_trigger.py:303`);
  - `system_prompt_file`, through `config_loader.py`.

  `tone` and `avoid` are read by nothing. Every behavior change therefore goes in `prompts.md`.
  `default_question` stays as it is (spec: missed questions unchanged).
- **No code changes.** The model name is already read from `OPENAI_MODEL` in `.env`
  (`ai_client.py:30`). `.env` is git-ignored, so the switch is an operator step. The committed
  template `.env.example` is updated to match so a new machine starts on the right model.
- **The 200-character cut in `ai_client.py`** cuts mid-word. It stays as it is: the 30-word limit
  keeps fortunes under it. Reading the question set (Step 5) watches for any ticket that hits it.
  Fix it in code only if one does.
- **Fortune behavior is judged by reading, not asserted.** A model's wording can't be pinned by a
  test. The automated tests guard only what is deterministic: the persona loads, its ticket fits
  the printer (already covered by `tests/test_smoke.py`), the dead 2025 rules are gone, and the
  almanac carries an "as of" date.
- **The question set lives in `_work/umbraco-2026-persona/assets/question-set.csv`.** It's
  increment-scoped. Its generic questions can move to `docs/` later if another persona wants them.
  Same `id,category,question` shape as `docs/baseline-script.csv`, so it reads familiarly.
- **Running the question set.** A shell loop over the CSV calling
  `.venv/bin/python app.py --persona umbraco-2026 --question "<q>" --dry-run`.
  - **Safe to run from Claude:** `app.py` with `--question` needs no mic and no keyboard, so it's
    not an interactive run in CLAUDE.md's sense.
  - **Costs:** each run is a real, paid model call. `gpt-4.1-mini` makes the whole set a matter of
    cents.
  - **No new script:** the loop lives in the reading notes, per the lean rule.
- **Almanac facts come from a web search, reviewed by the owner, before they reach the prompt.**
  Umbraco 18 is outside Claude's reliable knowledge. The draft lives in
  `_work/umbraco-2026-persona/notes/almanac-draft.md` with sources, so the owner reviews facts
  separately from prose.
- **Thresholds from the spec** (no more than 2 of 20 hedges; no more than 1 of 10 stray quirks)
  are proposals the owner confirms while reading Step 5's results.
- **Test file**: `tests/test_persona_umbraco_2026.py`. It follows the stack's `test_<flow>.py`
  convention, since it tests a persona's content, not a module.
- **Commands used** (all from `.agents/config/stack.md`):
  - `.venv/bin/python -m pytest -q`;
  - `.venv/bin/python app.py --list-personas`;
  - `.venv/bin/python app.py --persona … --question … --dry-run`.

  The venv lives at `/Users/dkardys/Sites/fortune-service/.venv/`. From this worktree, call it by
  that absolute path if `.venv/` is missing locally.

---

## Steps

Each step is designed to be completed independently in its own context window.
The step heading contains a ready-to-use prompt you can paste into a new session.

---

### Step 1 — Write the question set

> **Prompt**: Implement Step 1 of `_work/umbraco-2026-persona/plan.md`. Read
> `_work/umbraco-2026-persona/spec.md` (the Acceptance Criteria and Scenarios). Create
> `_work/umbraco-2026-persona/assets/question-set.csv` with columns `id,category,question`: the
> questions Step 5 will run through Narly to read the new persona's fortunes. Use the category
> list in "What to build". Include every concrete question from the spec's scenarios verbatim,
> then fill each category to its count; borrow generic questions from
> `docs/baseline-script.csv` where they fit. Questions are plain spoken English, as an attendee
> would say them aloud. No code changes. Commit the file.

**What to build**:
- `_work/umbraco-2026-persona/assets/question-set.csv`, with these categories:
  - `decision`: 20 yes/no or this-or-that questions. Not relationship, health, grief or legal
    questions. Include travel, risk, career, learning, one harmful-to-others, one
    against-own-interest ("deploy to production on Friday at 5pm").
  - `open`: 4 non-decision questions ("What does my week look like?").
  - `serious`: 6 questions: 2 relationship, 2 health, 1 grief, 1 legal. Include the two overlap
    cases from the spec's edge cases ("Should I move to Berlin for her?", "Should I have the
    surgery?").
  - `unrelated`: 10 questions with no Chicago, food, sports, birthday or Mats angle, as their own
    rows, not reused from `decision`, so each count stays clean.
  - `deflect`: 4 questions. 2 that should get an opinion ("When will I find love?", "What's the
    best CMS?") and 2 that should be deflected ("How do I install Umbraco 18?", "How much does
    Umbraco Cloud cost?").
  - `competitor`: 3 questions ("What's the worst CMS?", "Umbraco or WordPress?", "Is Sitecore any
    good?").
  - `mishear`: 5 questions with "Umbraco" misheard: en bronco, oom braco, embraco, umbrella co,
    umbroco. Add 1 question genuinely about the Denver Broncos.
  - `quirk`: 6 invitations: Cubs or Sox; the Bears; Narly's age; Mats; Chicago pizza; Malort.
  - `almanac`: 2 questions about Umbraco 18 ("What's the best thing in Umbraco 18?").
  - `echo`: 2 questions with a distinctive word ("Should I get a narwhal tattoo?").

**Validation**:
- [Automated]: `.venv/bin/python -c "import csv; rows=list(csv.DictReader(open('_work/umbraco-2026-persona/assets/question-set.csv'))); print(len(rows)); import collections; print(collections.Counter(r['category'] for r in rows))"`.
  Category counts match the list above.
- [Manual]: every spec scenario's question appears word for word.

---

### Step 2 — Switch the model and confirm it responds

> **Prompt**: Implement Step 2 of `_work/umbraco-2026-persona/plan.md`. The fortune model moves
> from `gpt-4o-mini` to `gpt-4.1-mini`. `ai_client.py` already reads the model from
> `OPENAI_MODEL`, so no Python changes. Change the value in the committed template
> `.env.example`. In `docs/testing.md`, add a short note that says which model Narly uses and
> that the operator sets `OPENAI_MODEL=gpt-4.1-mini` in `.env` on each machine that runs Narly,
> with `gpt-4.1` as the step up. Put it where the runbook first discusses `.env`. Plain,
> non-developer language, matching the runbook's tone. **Ask the owner to edit their own `.env`**:
> Claude never reads or writes `.env`, which holds the API key. Then run one real fortune,
> `.venv/bin/python app.py --persona umbraco-2026 --question "Should I go to Iceland next spring?" --dry-run`,
> timed with `time`. Report whether it succeeded and how long it took. Commit `.env.example` and
> `docs/testing.md`.

**What to build**:
- `.env.example`: `OPENAI_MODEL=gpt-4.1-mini`.
- `docs/testing.md`: a model note beside the existing `.env` guidance, near "One-time setup"
  step 6 or the "Replay a recording" paragraph that mentions the OpenAI key.
- The owner edits `.env` by hand.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` is still green. Nothing reads `.env.example` in
  tests.
- [Manual]: the timed `app.py` run prints a ticket with no model error. If it returns "model not
  found", the account lacks `gpt-4.1-mini`: stay on `gpt-4o-mini` and note it in the step report.
  The wall-clock time is recorded for the owner to judge at the booth.

---

### Step 3 — Draft the almanac for owner review

> **Prompt**: Implement Step 3 of `_work/umbraco-2026-persona/plan.md`. Use web search to
> gather this week's facts for Narly's almanac, and write them to
> `_work/umbraco-2026-persona/notes/almanac-draft.md`. Put a source link under each fact. The
> owner reviews this file before any fact reaches the prompt; mark every fact `[ ] reviewed`. Do
> not invent anything. If a fact can't be sourced, leave it out and say so. Keep each fact to one
> line, phrased as something Narly could allude to in a 30-word fortune. Sections are listed in
> "What to build". Commit the draft, then stop and ask the owner to review it.

**What to build**: `_work/umbraco-2026-persona/notes/almanac-draft.md`, with:
- An `As of: 2026-09-29` line at the top.
- **Umbraco 18**: 4–6 headline features or changes, and its release timing.
- **Competitors**: WordPress, Drupal, Sitecore, Contentful, Optimizely, Sanity, Adobe Experience
  Manager. One real trait each, plus a fond, sea-flavored tease drafted from it, in the spirit of
  "WordPress: a fine raft, if you enjoy bailing water".
- **Mats Persson**: confirm he is still CEO. Approved angles: the title, the legend, "quite the
  talker", "the secret to your success". Nothing about his private life.
- **Event**: Umbraco 2026 US Festival, Chicago; venue if sourced.
- **Chicago sports**: where the Bears stand this season; the Cubs and White Sox playoff status.
  Status only, no predictions.
- **Narly**: turns 2; created at the 2024 US Festival. This is from the owner, so it needs no
  source.

**Validation**:
- [Manual]: the owner ticks `[x] reviewed` on each fact, and corrects or deletes any that are
  wrong. **Step 4 does not start until every remaining fact is ticked.**

---

### Step 4 — Write the 2026 prompt

> **Prompt**: Implement Step 4 of `_work/umbraco-2026-persona/plan.md`. Rewrite
> `personas/umbraco-2026/prompts.md` (currently a copy of `default`) to implement the spec
> `_work/umbraco-2026-persona/spec.md` → Functional Requirements. Use the owner-reviewed facts in
> `_work/umbraco-2026-persona/notes/almanac-draft.md`; only facts ticked `[x] reviewed` may be
> used. Borrow the sea-song knowledge section from `personas/music/prompts.md`, keeping the
> shanties and classic songs of the sea and dropping the Revenirs material. **Test first**:
> create `tests/test_persona_umbraco_2026.py` with the three tests described below. Run
> `.venv/bin/python -m pytest -q tests/test_persona_umbraco_2026.py` and confirm they fail
> against the current copy. Then write the prompt and confirm they pass, along with the full
> suite. Also set `content.json`'s `tone` to describe the new voice; it's documentation, since no
> code reads it. Leave `header`, `footer`, `default_question` and `max_chars` unchanged. Commit.

**What to build**: `personas/umbraco-2026/prompts.md`, organised as:
1. **Role and base character.** Narly the Narwhal at the Umbraco 2026 US Festival, Chicago.
   Umbraco pride. Sea language and sea-song layering as seasoning.
2. **Verdicts.** Open with a clear verdict only for decision questions; ordinary fortune
   otherwise. Hedges rare.
3. **Which way the verdict leans.** Yes to brave and virtuous; playful no to harm or demeaning
   others; teasing no to things against the person's own interest.
4. **Serious questions.**
   - Big leaps get a brave verdict.
   - Relationships get a hedge.
   - Health, grief and legal questions get a blessing with no verdict and no advice.
   - Questions demeaning others get a dodge or a turn back toward kindness.
   - When categories overlap, the more cautious path wins.
5. **Deflect by intent.** Only tutorials, prices, schedules, and facts where being wrong matters.
   "Best" gets Umbraco; "worst" and comparisons name a competitor and tease it fondly, never
   trashing it. No real person is the target.
6. **Hearing "Umbraco".** Close-sounding words mean Umbraco, spelled right, never remarked on. A
   question clearly about the Denver Broncos stays about the Broncos.
7. **Quirks only when invited.** Mats (legend and title only), the birthday (turning 2), pizza,
   Malort, the Bears (suspicious of the hope), Cubs and Sox (both, favoring the Sox because cubs
   eat fish; no predictions).
8. **Narly's almanac.** The reviewed facts, with the `As of:` line.
9. **Verdict phrases.** A small bank of yes, no and maybe phrases, marked as inspiration, not a
   script.
10. **Question echo.** Work in a distinctive word from the question when there is one, within the
    word limit, never adding length.
11. **Examples.** 8–10 new tone examples showing the behavior: a verdict opening, an echo, a
    competitor tease, a serious-question blessing, a deflection, and quirks only on quirk
    questions. No food or sports in examples that aren't about them. Marked "do not repeat
    verbatim".
12. **Format rules**, kept from the current prompt: one fortune; 1–2 sentences; at most 30 words;
    no formatting; never break character; never mention being an AI; 32-character ticket.

Removed: the keyword deflection list, the "Anti-repetition" section, the "October 2023" line,
"Do not browse the web", and any stray command line.

**Test first**, in `tests/test_persona_umbraco_2026.py`. Load the persona with
`load_config("umbraco-2026")` and assert on `cfg["system_prompt"]`:
- `test_umbraco_2026_no_longer_deflects_by_keyword`: the prompt contains no keyword trigger list.
  Assert that the 2025 list's distinctive run `best, top, worst, compare` is absent.
- `test_umbraco_2026_drops_dead_2025_rules`: none of `October 2023`, `Anti-repetition` or
  `python serial_trigger.py` appears.
- `test_umbraco_2026_almanac_is_dated`: the prompt contains a line starting `As of:` followed by
  a date in `YYYY-MM-DD` form.

All three fail on the current copy of `default`: it holds the trigger list, the October line and
the anti-repetition section, and it has no `As of:` line. Confirm RED before writing the prompt.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q`. All tests pass, including the parameterised
  printer-width test for `umbraco-2026`.
- [Automated]: `.venv/bin/python app.py --list-personas` still lists `umbraco-2026`.
- [Manual]: a spot check. Run
  `.venv/bin/python app.py --persona umbraco-2026 --question "What's the best CMS?" --dry-run`;
  the ticket names Umbraco.

---

### Step 5 — Read the question set and tune

> **Prompt**: Implement Step 5 of `_work/umbraco-2026-persona/plan.md`. Run every question in
> `_work/umbraco-2026-persona/assets/question-set.csv` once through
> `.venv/bin/python app.py --persona umbraco-2026 --question "<q>" --dry-run`, using a shell loop
> over the CSV. These are real, paid model calls on the model set in Step 2, at a few cents for
> the set. Record every ticket under its id and category in
> `_work/umbraco-2026-persona/notes/reading.md`, then score against the spec's Acceptance
> Criteria:
> - hedges among the 20 `decision` questions (target no more than 2);
> - quirk mentions among the 10 `unrelated` questions (target no more than 1);
> - the `serious`, `deflect`, `competitor`, `mishear`, `quirk` and `almanac` stances;
> - whether any ticket runs over 30 words, or looks cut off at 200 characters.
>
> Put the loop command at the top of the notes so it can be re-run. If a criterion misses, make
> one targeted edit to `personas/umbraco-2026/prompts.md` (usually an example or a sharper rule)
> and re-run only the affected category. Stop after two tuning rounds and report what still
> misses. The owner reads the notes and confirms or adjusts the thresholds. Keep
> `.venv/bin/python -m pytest -q` green. Commit the notes and any prompt edits.

**What to build**:
- `_work/umbraco-2026-persona/notes/reading.md`: the run command, a results table (id,
  category, ticket, pass or miss), the score summary, and the tuning edits made, round by round.
- Targeted edits to `personas/umbraco-2026/prompts.md` if needed.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` is green after any prompt edit.
- [Manual]: the owner reads `reading.md`:
  - agrees with each pass or miss call;
  - confirms the thresholds;
  - decides whether the echo stays (drop it if tickets run long);
  - and whether to step up to `gpt-4.1` if tickets feel flat.

---

### Step 6 — Update the project docs and run it on the hardware

> **Prompt**: Implement Step 6 of `_work/umbraco-2026-persona/plan.md`. Update the docs that
> name the personas:
> - In `CLAUDE.md`, change the Personas line so `umbraco-2026` is described as the Umbraco 2026
>   festival persona, not a copy of `default`.
> - In `.agents/config/paths.md`, update the `personas/<name>/` row, which still lists three
>   personas.
> - In `.agents/config/stack.md`, update the `--list-personas` example, which still shows three.
> - In `ROADMAP.md` → Now, add a short entry for the Umbraco 2026 persona, pointing at
>   `_work/umbraco-2026-persona/spec.md`.
>
> Keep the edits minimal and in each file's existing style. Run `.venv/bin/python -m pytest -q`.
> Commit. Then **ask the owner** to run one full hardware fortune in a plain terminal (not
> through Claude):
> `.venv/bin/python serial_trigger.py --mode hardware --persona umbraco-2026`, speaking an Umbraco
> question into the AM8. They confirm the ticket prints and answers the question.

**What to build**: the doc edits in `CLAUDE.md`, `.agents/config/paths.md`,
`.agents/config/stack.md` and `ROADMAP.md`.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` is green.
- [Manual]: the owner's hardware run. Coin, then mic, then a printed ticket that answers a spoken
  question containing "Umbraco", with "Umbraco" spelled correctly on the ticket.

---

### Final — Record the durable behavior *(a spell you cast, not an implement-step)*

Cast directly after Step 6: `/feature update personas`.

> **Prompt**: Run `/feature update personas` to verify the living behavioral doc reflects the
> actual implementation. Review each scenario against `personas/umbraco-2026/prompts.md` and the
> reading results in `_work/umbraco-2026-persona/notes/reading.md`. Update any scenario where the
> behavior diverged from the draft, for example thresholds the owner adjusted, or the echo
> dropped. Fill in the test coverage table:
> - the three deterministic guards point at `tests/test_persona_umbraco_2026.py` and
>   `tests/test_smoke.py` with line numbers;
> - scenarios proved only by reading fortunes are marked
>   `Ruled out — model wording can't be asserted; checked by reading the question set (notes/reading.md)`,
>   or `Not covered` where the reading didn't exercise them.
>
> Remove the "Draft" banner. Commit the verified doc.
>
> **Validation**: every scenario matches observed behavior; the coverage table has no unexpected
> "Not covered" gaps.

---

## File Summary

| Action | File |
|--------|------|
| Create | `_work/umbraco-2026-persona/assets/question-set.csv` |
| Modify | `.env.example` |
| Modify | `docs/testing.md` |
| Create | `_work/umbraco-2026-persona/notes/almanac-draft.md` |
| Create | `tests/test_persona_umbraco_2026.py` |
| Modify | `personas/umbraco-2026/prompts.md` |
| Modify | `personas/umbraco-2026/content.json` |
| Create | `_work/umbraco-2026-persona/notes/reading.md` |
| Modify | `CLAUDE.md` |
| Modify | `.agents/config/paths.md` |
| Modify | `.agents/config/stack.md` |
| Modify | `ROADMAP.md` |
| _(operator, not committed)_ Modify | `.env` (`OPENAI_MODEL=gpt-4.1-mini`) |
| Create/Update | `_features/personas.md` (the new capability's feature doc) |
