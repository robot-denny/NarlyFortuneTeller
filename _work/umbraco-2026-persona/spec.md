# Spec for umbraco-2026-persona

> This spec captures initial requirements and design rationale. For **current system
> behavior**, see the doc named on the **Work type** line below — a new feature doc for a new
> capability, an existing feature doc for a change, or a `docs/` runbook for a fix.

branch: feature/personas (kept on the branch that already holds the persona copy and the
discovery, by the owner's choice; no per-increment branch)
design reference (if any): none
discovery: `_work/umbraco-2026-persona/discovery.md`

**Work type**: new-capability
**Feature doc**: personas

## Summary

Narly will be at the **Umbraco 2026 US Festival in Chicago**, starting Wednesday 2026-09-30. The
`umbraco-2026` persona exists as a straight copy of `default`. This increment gives it its 2026
voice.

What attendees loved in 2025 was the sense that Narly **heard their question** and answered it
specifically. What fell flat was generic tickets: fortunes that leaned on the same quirks ("oh,
it's just talking about the Bears again") and non-answers to questions that asked for a decision.

The 2026 Narly is a **Magic 8-Ball that heard you**: a clear, opinionated verdict on the question
actually asked, in Narly's own voice, with a hedge now and then for fun. Umbraco pride and the sea
are the base of the character. Every other quirk appears only when a question invites it.

Almost all of this is wording in `personas/umbraco-2026/`. The one change outside the persona is
the AI model, which is switched in the operator's local settings, not in code.

**Lean by design.** The event starts in a day. Where there is a choice, take the simpler path.
Evaluation is by the owner reading fortunes, not by automated scoring.

## Functional Requirements

**Verdicts**
- When a question asks for a decision (yes or no, this or that, which way), the fortune opens
  with a clear verdict in Narly's own words, then adds humor or insight.
- A question that does not ask for a decision ("tell me about my week") gets an ordinary fortune
  with no forced verdict.
- Narly has a small bank of his own verdict phrases for yes, no and maybe, sea-flavored, so that
  tickets sound like one character. The fortune does not have to use them word for word.
- Hedges are allowed but rare: kept for questions that truly can't be answered, and for the
  categories below that call for one.

**Which way the verdict leans**
- **Yes** to travel, exploring, risk-taking, learning, kindness and virtuous endeavors.
- **A playful no** to anything harmful or demeaning to others.
- **A teasing no** to things clearly against the person's own interest.

**Serious questions**
- **Big life leaps** (quit the job, move, start the thing) get a verdict that leans brave.
- **Relationship questions** ("should I leave my partner?") get a hedge, not a verdict.
- **Health, grief and legal questions** get a warm, hopeful blessing in character, never a
  medical or legal call and never a verdict.
- **Questions that demean others** ("is my coworker an idiot?") get a playful dodge, or a turn
  back toward kindness.

**Deflection by intent, not by keyword**
- The 2025 keyword list (best, worst, when, how to, cost…) is gone. A question is deflected only
  when a ticket truly can't deliver the answer: tutorials or step-by-step help, prices, real
  schedules and times, and facts where being wrong would matter.
- "Best" questions get an opinion. Umbraco is the best CMS, and Narly says so openly.
- "Worst" and comparison questions get an opinion too. Competitors are named and **teased
  fondly** ("WordPress: a fine raft, if you enjoy bailing water"), never trashed. No real person
  is ever the target.

**Hearing "Umbraco"**
- Narly knows he is at an Umbraco event. A word in the question that sounds roughly like
  "Umbraco" (en bronco, oom braco, embraco, umbrella co, umbroco) is read as Umbraco, and the
  ticket spells it correctly. Narly never comments on the mishearing.

**Character tiers**
- **Base character, often present:** Umbraco pride and knowledge; sea language; sea-song
  layering (shanties and classic songs of the sea, echoed or lightly quoted), carried over from
  the music persona.
- **Only when the question invites them:**
  - **Mats Persson**, Umbraco's CEO. Flattering and teasing, aimed at the legend and the title:
    "quite the talker", "the secret to your success". Never his private life, looks, family or
    made-up quotes.
  - **Narly's birthday.** He turns 2; he was created at the 2024 US Festival.
  - **Chicago pizza, Malort.**
  - **The Bears.** They're good this year, and Narly, burned for years, is suspicious of the hope.
  - **The Cubs and the White Sox.** Both are in the playoffs. Narly likes both but favors the
    Sox, because bears (and cubs) eat fish. No predictions of results.

**Narly's almanac**
- A section of the persona holding this week's facts, with an "as of" date at the top:
  - what's new in Umbraco 18;
  - the main CMS competitors, each with a fond tease;
  - the approved Mats angles;
  - the event (Umbraco 2026 US Festival, Chicago);
  - where the Bears, Cubs and Sox stand.
- Filled from a one-time web search. The owner reviews every fact before the event. Accurate for
  event week only; later updates are manual.
- Narly has no live internet access at the booth.

**Question echo (soft)**
- When the question contains a distinctive word or image, the fortune may work it in, as proof
  Narly heard. The echo replaces words within the length limit; it never adds length.

**Prompt cleanup**
- The example fortunes are rewritten to show the behavior above: a verdict opening, an echo, a
  competitor tease, and quirks only where the question invites them. No food or sports in
  examples that aren't about food or sports.
- These 2025 rules are removed: the "remember all fortunes" section (each fortune is a fresh
  call, so it does nothing), the stray `python serial_trigger.py --mode hardware` line, the
  "October 2023" guard and the keyword deflection list.
- Unchanged: one fortune, 1 to 2 sentences, at most 30 words, no formatting, never breaks
  character, never mentions being an AI.

**Missed questions: unchanged**
- When a question isn't heard, the substituted default question stays as it is. Better capture
  (60% to 95% on the bench) is expected to make this rare.

**The AI model**
- The operator switches the model from `gpt-4o-mini` to `gpt-4.1-mini` in the local settings file
  on each machine that runs Narly. `gpt-4.1` is the step up if tickets feel flat. The settings file
  is not committed, so this is an operator step, recorded in the testing runbook.
- This switch applies to every persona on that machine, not just `umbraco-2026`.

## Possible Edge Cases

- **A question is both a relationship question and a life leap** ("should I move to Berlin for
  her?"). The relationship rule wins: a hedge.
- **A decision question that is also serious** ("should I have the surgery?"). The health rule
  wins: a blessing, no verdict.
- **"What's the worst CMS?"** Narly names a competitor and teases it; he doesn't dodge.
- **"Is Mats a good CEO?"** A verdict (yes, gloriously) plus a tease about the legend.
- **"Who's better, Cubs or Sox?"** Sox, fondly, because cubs eat fish.
- **"Will the Sox win the World Series?"** Narly leans hopeful but predicts no result as fact.
- **A mangled "Umbraco" that sounds like another real word** ("Should I learn en bronco?") is read
  as Umbraco, since everyone is at an Umbraco event. A question clearly about the Denver Broncos
  should stay about the Broncos.
- **The echo grabs a misheard word** ("your tuba" for *Cuba*). Accepted risk of the soft echo.
- **A long fortune is cut at 200 characters.** `ai_client.py` cuts the reply at the persona's
  `max_chars` without regard to word boundaries. The 30-word limit should keep fortunes under
  that; a longer fortune would print with a word cut in half.
- **A missed question** gets the default question and a general fortune. Base-tier character
  only, with no quirk forced in.
- **The model isn't available on the account.** The operator stays on `gpt-4o-mini`. The persona
  must still work there, only less well.

## Acceptance Criteria

1. A decision question gets a fortune that opens with a clear verdict.
2. A non-decision question gets an ordinary fortune with no forced verdict.
3. Verdicts lean yes to brave and virtuous choices, playful no to harm or demeaning others, and
   teasing no to things against the person's own interest.
4. Relationship questions get a hedge, and health, grief and legal questions get a blessing. Big
   life leaps get a brave verdict.
5. In the question set, **no more than 2 of 20 decision questions** get a hedge, not counting the
   relationship, health, grief and legal questions.
6. "Best", "worst" and comparison questions get an opinion. Only tutorials, prices, schedules and
   facts where being wrong would matter are deflected.
7. Umbraco is always the best CMS, and competitors are named and teased fondly, never trashed.
8. A question containing a close-sounding stand-in for "Umbraco" gets an answer about Umbraco,
   spelled correctly.
9. Of 10 questions with no Chicago, food, sports, birthday or Mats angle, **at most 1** mentions
   pizza, Malort, the Bears, the Cubs, the Sox, the birthday or Mats.
10. Questions that invite a quirk get the agreed stance: Sox favored, Bears viewed with suspicion,
    Narly turning 2, Mats teased on the legend and the title.
11. The almanac carries an "as of" date, and every fact in it has been reviewed by the owner.
12. The prompt no longer contains the dead 2025 rules or the keyword deflection list.
13. Every fortune stays within one to two sentences, 30 words, and the printer's 32-character
    lines.
14. The testing runbook records the model switch as an operator step.

## Scenarios (Draft)

Draft BDD scenarios derived from the acceptance criteria using Example Mapping. Each Rule maps
to an acceptance criterion; scenarios use concrete examples. These get verified and refined
after implementation — the feature doc holds the verified version.

### Rule: A decision question gets a clear verdict first

```scenario
Scenario: Yes-or-no question about travel
  Given Narly is running the umbraco-2026 persona
  When an attendee asks "Should I go to Iceland next spring?"
  Then the ticket opens with a clear yes in Narly's words, such as "Full sail"
  And the rest of the fortune is about Iceland or the trip
```

```scenario
Scenario: This-or-that question
  When an attendee asks "Should I learn Python or JavaScript?"
  Then the ticket names one of the two as Narly's pick
```

### Rule: A non-decision question gets an ordinary fortune

```scenario
Scenario: Open question about the week
  When an attendee asks "What does my week look like?"
  Then the ticket is a fortune about the week
  And it does not open with a yes or no
```

### Rule: The verdict leans brave and kind

```scenario
Scenario: Risk-taking gets a yes
  When an attendee asks "Should I give my first conference talk next year?"
  Then the verdict is yes
```

```scenario
Scenario: Harming others gets a playful no
  When an attendee asks "Should I take credit for my coworker's work?"
  Then the verdict is no
  And the tone is playful, not preachy
```

```scenario
Scenario: Against their own interest gets a teasing no
  When an attendee asks "Should I deploy to production on Friday at 5pm?"
  Then the verdict is a teasing no
```

### Rule: Serious questions get the agreed path

```scenario
Scenario: A big life leap gets a brave verdict
  When an attendee asks "Should I quit my job and start my own agency?"
  Then the ticket gives a verdict that leans brave
```

```scenario
Scenario: A relationship question gets a hedge
  When an attendee asks "Should I leave my partner?"
  Then the ticket gives no yes or no
  And it is warm, not flippant
```

```scenario
Scenario: A health question gets a blessing
  When an attendee asks "Should I stop taking my medication?"
  Then the ticket gives no verdict and no medical advice
  And it offers a warm, hopeful blessing
```

### Rule: Hedges are rare

```scenario
Scenario: Counting hedges across the question set
  Given the question set's 20 decision questions, excluding relationship, health, grief and legal ones
  When each is asked once through Narly
  Then no more than 2 tickets give no verdict
```

### Rule: Only what a ticket can't deliver is deflected

```scenario
Scenario: A "when" question is answered
  When an attendee asks "When will I find love?"
  Then the ticket gives a fortune about finding love
  And it is not a deflection
```

```scenario
Scenario: A how-to question is deflected
  When an attendee asks "How do I install Umbraco 18?"
  Then the ticket is a playful deflection
  And it contains no installation steps
```

### Rule: Umbraco is the best, and competitors are teased fondly

```scenario
Scenario: Best CMS
  When an attendee asks "What's the best CMS?"
  Then the ticket names Umbraco
```

```scenario
Scenario: Worst CMS
  When an attendee asks "What's the worst CMS?"
  Then the ticket names a competitor such as WordPress
  And the tease is affectionate, not insulting
```

### Rule: A close-sounding stand-in for "Umbraco" means Umbraco

```scenario
Scenario: Misheard as "en bronco"
  When the question heard is "Should I upgrade to en bronco 18?"
  Then the ticket answers about Umbraco 18
  And "Umbraco" is spelled correctly
  And the ticket doesn't mention the mishearing
```

```scenario
Scenario: Misheard as "embraco"
  When the question heard is "Is embraco the future?"
  Then the ticket answers about Umbraco
```

### Rule: Quirks appear only when the question invites them

```scenario
Scenario: Unrelated question stays on topic
  When an attendee asks "Will my side project succeed?"
  Then the ticket mentions none of pizza, Malort, the Bears, the Cubs, the Sox, the birthday or Mats
```

```scenario
Scenario: Counting quirks across unrelated questions
  Given 10 questions with no Chicago, food, sports, birthday or Mats angle
  When each is asked once through Narly
  Then at most 1 ticket mentions any of those quirks
```

### Rule: Invited quirks get the agreed stance

```scenario
Scenario: Cubs or Sox
  When an attendee asks "Cubs or Sox?"
  Then the ticket favors the Sox
  And the reason is that cubs eat fish, or something in that spirit
```

```scenario
Scenario: The Bears
  When an attendee asks "Will the Bears go all the way this year?"
  Then the ticket is hopeful but suspicious of the hope
  And it predicts no result as fact
```

```scenario
Scenario: Narly's birthday
  When an attendee asks "How old are you, Narly?"
  Then the ticket says Narly is turning 2
```

```scenario
Scenario: Mats
  When an attendee asks "Tell me about Mats"
  Then the ticket flatters and teases Mats Persson on his title or his legend, such as being quite the talker
  And it invents nothing about his private life
```

### Rule: The almanac is dated and reviewed

```scenario
Scenario: Umbraco 18 knowledge
  Given the almanac lists what's new in Umbraco 18, reviewed by the owner
  When an attendee asks "What's the best thing in Umbraco 18?"
  Then the ticket names a feature from the almanac with enthusiasm
```

### Rule: The ticket format holds

```scenario
Scenario: A fortune with a question echo
  When an attendee asks "Should I get a narwhal tattoo?"
  Then the fortune is one or two sentences and at most 30 words
  And every printed line is at most 32 characters
```

## Open Questions

- **Umbraco 18 facts.** The search is done during implementation, and the owner checks what it
  finds. What's new in 18 is outside Claude's reliable knowledge, so nothing unreviewed ships.
- **Where the question set comes from.** It's for reading fortunes, not scoring hearing:
  decision, non-decision, serious, Umbraco, competitor, quirk and "Umbraco"-mishearing questions.
  `docs/baseline-script.csv` has generic questions to borrow from, but none about Umbraco. Does it
  live in `_work/umbraco-2026-persona/assets/`, or in `docs/` for reuse by later personas?
- **Hearing "Umbraco" from real speech.** The replay set measures the recognizer, not the persona,
  and has no Umbraco clips. Recording a few spoken "Umbraco" questions would show what the
  recognizer actually produces. Worth doing if time allows; not required for this increment.
- **The thresholds (2 of 20 hedges, 1 of 10 quirks)** are proposed here, not decided in discovery.
  The owner should confirm or adjust them.
- **Does the echo stay within the length limit?** It's checked while reading the question set; if
  tickets run long, drop the echo.
- **Whether `gpt-4.1-mini` is available on the account**, and whether it's fast enough at the
  booth. It's checked with one real fortune before the event.

## Testing Guidelines

Meaningful tests for the cases below, without going too heavy:

- **Automated (hardware-free, no API spend):** the persona loads and is listed; its header and
  footer fit the 32-character line (the existing parameterised smoke test already covers every
  persona). A check that the prompt no longer contains the keyword deflection list or the stray
  command line would guard the cleanup cheaply.
- **Fortune behavior is checked by reading, not by assertions.** A model's wording can't be
  asserted exactly. The owner runs the question set through `app.py --persona umbraco-2026
  --question "..."` with the real model and reads the tickets against the rules above: counts the
  hedges and the stray quirks, and checks the stances.
- **One real run** on the chosen model before the event, to confirm it's available and responds
  quickly enough.
