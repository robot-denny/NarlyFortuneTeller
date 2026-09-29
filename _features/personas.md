# Feature: Personas

A persona is the voice Narly speaks in at an event: what he knows, what he cares about, and how
his fortunes answer an attendee's question. The operator picks one when Narly starts, and the
`default` persona is always the fallback. The `umbraco-2026` persona, for the Umbraco 2026 US
Festival in Chicago, gives a clear, opinionated verdict on the question actually asked. He is
openly proud of Umbraco, and he brings in his quirks only when a question invites them.

**Source**: `_work/umbraco-2026-persona/spec.md`
**Last verified**: 2026-09-29

---

## Increments

- [x] 2026-09-29 — Umbraco 2026 persona (`_work/umbraco-2026-persona/spec.md`)
- [ ] Backfill the `default`, `music` and `umbraco-2025` voices from their prompts (no spec yet)
- [ ] Try Claude (Haiku 4.5) as the fortune provider (no spec yet)
- [ ] Spell "Umbraco" right at the recognizer with a vocabulary hint (roadmap Increment 4, no
      spec yet)

---

## Behaviors

### Rule: The operator chooses a persona when Narly starts

```scenario
Scenario: Listing the personas
  Given Narly has the personas default, music, umbraco-2025 and umbraco-2026
  When the operator asks Narly to list its personas
  Then those four are listed
```

```scenario
Scenario: Every persona's ticket fits the printer
  Given any of the four personas
  When Narly prints a ticket for it
  Then no printed line is wider than 32 characters, header and footer included
```

### Rule: A decision question gets a clear verdict first

```scenario
Scenario: Yes-or-no question about travel
  Given Narly is running the umbraco-2026 persona
  When an attendee asks "Should I go to Iceland next spring?"
  Then the ticket opens with a clear yes in Narly's words, such as "Hoist the sails"
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
  Then the verdict is no, such as "Belay that, sailor!"
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

```scenario
Scenario: A legal question gets a blessing
  When an attendee asks "Should I sue my landlord?"
  Then the ticket gives no verdict and nothing that reads as a legal opinion
  And it may point toward good counsel in general terms
```

### Rule: Hedges are rare

```scenario
Scenario: Counting hedges across the question set
  Given the question set's 20 decision questions, excluding relationship, health, grief and legal ones
  When each is asked once through Narly
  Then no more than 2 tickets give no verdict
```

### Rule: Only what a ticket can't deliver is deflected

Deflection depends on what the question asks for, not on the words in it.

```scenario
Scenario: The persona holds no list of trigger words
  Given the umbraco-2026 persona
  When its instructions are loaded
  Then they contain no list of words that trigger a deflection
```

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

```scenario
Scenario: A named competitor gets its own tease
  When an attendee asks "Is Sitecore any good?"
  Then the ticket teases Sitecore with Sitecore's own tease, not another competitor's
  And it steers toward Umbraco
```

### Rule: Umbraco comes up when the question invites it

Umbraco pride is part of Narly's character, not a topic to slip into every ticket. It comes up
for questions about Umbraco, CMSs, websites, development, tech careers or the festival.

```scenario
Scenario: A development question may mention Umbraco
  When an attendee asks "Should I learn Python or JavaScript?"
  Then the ticket may bring Umbraco into its answer
```

```scenario
Scenario: A question about the garden stays about the garden
  When an attendee asks "Will my garden grow this summer?"
  Then the ticket does not mention Umbraco or any of its features
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
  And the misheard word does not appear on the ticket
```

```scenario
Scenario: A spoken question at the booth
  Given Narly is running on the booth hardware with the umbraco-2026 persona
  When an attendee speaks a question with "Umbraco" in it and the recognizer hears "embraco"
  Then the printed ticket answers about Umbraco, spelled correctly
```

```scenario
Scenario: A question really about the Denver Broncos
  When an attendee asks "Will the Denver Broncos make the playoffs?"
  Then the ticket is about the Broncos, not Umbraco
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
  And the reason is that bears (and cubs) eat fish
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
  Then the ticket says Narly is turning 2, born at the 2024 US Festival
```

```scenario
Scenario: Mats
  When an attendee asks "Tell me about Mats"
  Then the ticket flatters and teases Mats Persson on his title or his legend, such as being quite the talker
  And it invents nothing about his private life
```

### Rule: The almanac is dated and reviewed

```scenario
Scenario: The almanac says how current it is
  Given the umbraco-2026 persona
  When its instructions are loaded
  Then the almanac carries an "As of" date
```

```scenario
Scenario: Umbraco 18 knowledge
  Given the almanac lists what's new in Umbraco 18, reviewed by the owner
  When an attendee asks "What's the best thing in Umbraco 18?"
  Then the ticket names a feature from the almanac with enthusiasm, such as Elements
```

---

## Edge Cases

### Rule: The more cautious path wins when categories overlap

```scenario
Scenario: A relationship question that is also a life leap
  When an attendee asks "Should I move to Berlin for her?"
  Then the ticket gives a hedge, not a verdict
```

```scenario
Scenario: A decision question about health
  When an attendee asks "Should I have the surgery?"
  Then the ticket gives a blessing, not a verdict
```

### Rule: A misheard word that sounds like a rival company

```scenario
Scenario: Misheard as "umbrella co"
  When the question heard is "Is umbrella co the best CMS?"
  Then the ticket steers to Umbraco
  And the misheard word does not appear on the ticket
  But the ticket may open with a "no", as if "umbrella co" were a rival
```

### Rule: An unknown persona falls back to default

```scenario
Scenario: The operator names a persona that doesn't exist
  When the operator starts Narly with a persona called "umbraco-2027"
  Then Narly warns that it wasn't found and runs the default persona
```

### Rule: The ticket stays inside the printer's safe zone

The persona aims for one or two sentences of about 25 words, never more than 30. A few tickets run
one or two words over. None comes near the 200-character limit, beyond which Narly cuts the text off.

```scenario
Scenario: A fortune with a question echo
  When an attendee asks "Should I get a narwhal tattoo?"
  Then the fortune is at most 30 words, and may work in the narwhal
  And every printed line is at most 32 characters
```

---

## Test Coverage

| Scenario | Test File | Status |
|----------|-----------|--------|
| Listing the personas | `tests/test_smoke.py:L15` | Covered |
| Every persona's ticket fits the printer | `tests/test_smoke.py:L23` | Covered |
| Yes-or-no question about travel | — | Not covered |
| This-or-that question | — | Not covered |
| Open question about the week | — | Not covered |
| Risk-taking gets a yes | — | Not covered |
| Harming others gets a playful no | — | Not covered |
| Against their own interest gets a teasing no | — | Not covered |
| A big life leap gets a brave verdict | — | Not covered |
| A relationship question gets a hedge | — | Not covered |
| A health question gets a blessing | — | Not covered |
| A legal question gets a blessing | — | Not covered |
| Counting hedges across the question set | — | Not covered |
| The persona holds no list of trigger words | `tests/test_persona_umbraco_2026.py:L19` | Covered |
| A "when" question is answered | — | Not covered |
| A how-to question is deflected | — | Not covered |
| Best CMS | — | Not covered |
| Worst CMS | — | Not covered |
| A named competitor gets its own tease | — | Not covered |
| A development question may mention Umbraco | — | Not covered |
| A question about the garden stays about the garden | — | Not covered |
| Misheard as "en bronco" | — | Not covered |
| Misheard as "embraco" | — | Not covered |
| A spoken question at the booth | — | Not covered |
| A question really about the Denver Broncos | — | Not covered |
| Unrelated question stays on topic | — | Not covered |
| Counting quirks across unrelated questions | — | Not covered |
| Cubs or Sox | — | Not covered |
| The Bears | — | Not covered |
| Narly's birthday | — | Not covered |
| Mats | — | Not covered |
| The almanac says how current it is | `tests/test_persona_umbraco_2026.py:L31` | Covered |
| Umbraco 18 knowledge | — | Not covered |
| A relationship question that is also a life leap | — | Not covered |
| A decision question about health | — | Not covered |
| Misheard as "umbrella co" | — | Not covered |
| The operator names a persona that doesn't exist | — | Not covered (code-derived) |
| A fortune with a question echo | — | Not covered |

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

### Checked by reading, not by a test

Nothing can assert a model's wording, so the fortune scenarios are checked by reading tickets. The
latest reading is round 4 of `_work/umbraco-2026-persona/notes/reading.md` (2026-09-29,
`gpt-4.1-mini`, one ticket per question, raw output in `run-6-round4.txt`). A reading is evidence,
not a proof: each question was asked once, and the model can answer differently next time. That's
why these rows stay `Not covered`. Whether to mark them `Ruled out` is the project's decision to
make.

- **Seen in round 4:** every scenario above matched its ticket, except these two:
  - **A how-to question is deflected:** missed in round 4. #43 gave vague install steps; it passed
    in rounds 1 to 3.
  - **Worst CMS:** missed in round 4. #45 named no competitor; it passed in rounds 1 to 3.
- **Counts:** 0 of 20 decision questions hedged, and 0 of 10 unrelated questions mentioned a quirk.
- **Mishearings:** no misheard word appeared on any ticket.
- **Length:** the longest ticket was 172 characters. 5 of 63 tickets ran 31 to 32 words.
- **A spoken question at the booth:** seen on the booth hardware on 2026-09-29. The recognizer heard
  "embraco", and the printed ticket said "Umbraco".

---

## Revision Notes

- 2026-09-29: Draft scenarios from initial spec
- 2026-09-29: Verified against the implementation and four rounds of reading the question set.
  - **Removed:** the draft banner.
  - **New rules:** Umbraco comes up only when the question invites it, a legal question gets a
    blessing, and each competitor gets its own tease.
  - **New scenarios:** the booth hardware check, the Broncos question, and the "umbrella co" edge
    case, which may open with a "no".
  - **From the code:** listing personas, the printer-width check for every persona, and the fallback
    to default for an unknown persona. That last one is code-derived and untested.
  - **Changed to match the tickets:** the travel verdict example is "Hoist the sails" (was "Full
    sail"), the Cubs or Sox reason is "bears eat fish", and length now reads as a safe zone rather
    than a hard 30-word rule.
