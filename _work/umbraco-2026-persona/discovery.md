# Discovery: Umbraco 2026 Persona

_Discovery input for `/spec`, produced by `/explore` on 2026-09-29. Scope: heavyweight._

## Problem framing
- **Who:** attendees at the Umbraco 2026 US Festival in Chicago, mostly developers, designers and
  marketers. What they loved in 2025: the sense that Narly *heard* the question and gave a clear,
  specific answer. Humor and insight came second. Worth keeping.
- **Observed:** too many tickets felt generic ("oh, it's just talking about the Bears again").
  Many were likely missed captures. When a question isn't heard, `serial_trigger.py` swaps in
  `default_question`, and with nothing to answer the model falls back on the persona's strongest
  quirks. Heard questions also got too many non-answers, partly because the 2025 prompt deflects any
  question *containing* words like best, worst, when, how to. People were less amazed, not upset.
- **Assumed, not yet tested:** the birthday, "Umbraco is the best", the competitor teasing.
  **Observed working:** sea-song layering (music persona) and Mats teasing (Mats asked about himself
  in 2025 and loved it).
- **In one sentence:** too many tickets felt generic, so for 2026 Narly should give a clear,
  opinionated verdict on the question actually asked, in his own voice, with a hedge now and then
  for fun.

## Outcomes sought
- People say Narly has "a lot more opinions" than last year: a Magic 8-Ball that heard you, with
  context and Narly's own phrasing.
- Hedges are rare, not banned. Checkable on the replay set by counting non-answers.

## Options considered
- **Verdict mechanism:** prompt rule only / verdict first / values stance / hedges rationed in code.
  Code rationing is the only real control over how often hedges happen (calls are stateless), but it
  adds a moving part and can hand a "maybe" to a question that deserved a yes.
- **Deflection:** trim the word list / deflect by intent / no deflection. Word lists misfire ("When
  will I find love?" gets deflected); no deflection prints made-up tutorials.
- **Hearing "Umbraco":** recognizer vocabulary hint (root fix, belongs to Increment 4) / code alias
  list (predictable, but only catches listed mishearings) / prompt inference from event context
  (no code, invisible in logs).
- **Missed questions:** leave as is / tell Narly the words were lost (no code, via `default_question`
  text) / rotate a topic in code (real variety, for about 5% of tickets).
- **Quirk dosing:** frequency words (2025 approach, failed) / quirks only when the question invites
  them / flavor rationed in code (forces flavor onto questions where it doesn't fit).
- **Current knowledge:** almanac baked into the prompt / live web search per question / prefetch,
  review, bake in. Live search costs wait time at the booth, money per call, dependence on venue
  wifi, links in the ticket, and the ability to test offline, for freshness a 30-word ticket
  doesn't need.

## Trade-offs & second-order effects
- **Assertiveness meets serious questions:** a confident verdict on health or grief questions,
  printed and read aloud, could land badly. This needs its own path (below).
- **Missed questions still fall back on quirks:** with "leave as is", quirk dosing now also decides
  what those roughly 1-in-20 tickets say.
- **Question echo:** it strengthens the "it heard me" effect, but can echo a misheard word and may
  lengthen tickets.
- **Model upgrade:** newer reasoning GPT models can be slow and reject `temperature`, which
  `ai_client.py` sets. Speed at the booth matters as much as intelligence.
- **Almanac is time-bound:** accurate for event week only; anyone reusing it must update it by hand.

## Direction
Chosen. Almost all of it is prompt and `content.json` work in `personas/umbraco-2026/`:
- **Verdict first, only for decision questions** (yes/no, this-or-that, which way). Other questions
  get a normal fortune.
- **Values stance:**
  - lean yes to travel, risk, learning and virtue;
  - playful no to anything harmful or demeaning to others;
  - teasing no to things clearly against the person's own interest.
- **Serious-question split:**
  - big life leaps get a verdict, leaning brave;
  - health, grief and legal questions get a warm blessing and no verdict;
  - questions demeaning others get a playful dodge or a turn back toward kindness.
- **Deflect by intent**, not by word list. Deflect only tutorials, prices, schedules and facts where
  being wrong matters. Best/worst get opinions: Umbraco is the best, and competitors are named and
  teased fondly ("WordPress: a fine raft, if you enjoy bailing water"), never trashed.
- **"Umbraco" hearing:** a stronger prompt inference rule, since everyone is at an Umbraco event.
  Recognizer vocabulary hints wait for Increment 4 if results stay poor.
- **Missed questions:** leave as is, counting on better capture.
- **Quirk tiers:**
  - base character: Umbraco pride, sea and sea-song language (from the music persona);
  - only when the question invites them: Mats, the birthday, pizza, the Bears, Malort, Cubs/Sox.
- **Almanac section**, filled by a one-time reviewed search, with an "as of" date at the top:
  - Umbraco 18 features;
  - competitors, with a tease for each;
  - Mats angles: the legend and the title, "quite the talker", "the secret to your success". Never
    his private life or made-up quotes;
  - Chicago this week: the Bears are good this year and Narly is suspicious of the hope; the Cubs
    and Sox are both in the playoffs, with no result predictions.
- **Also:**
  - rewrite the example fortunes to model the behavior we want;
  - add a bank of Narly's own verdict phrases;
  - clear out dead rules: the memory section, the stray `python serial_trigger.py` line, the
    "October 2023" guard;
  - a soft question echo, only when a distinctive word is there and within the 30-word limit.
- **Rejected:** hedges rationed in code, live web search, code-side alias list, topic rotation in
  code, birthday header on the ticket.

## Resolved after discovery
- **Model:** stay on OpenAI; switch `OPENAI_MODEL` in `.env` to `gpt-4.1-mini`, with no code
  change (non-reasoning, fast, accepts `temperature`, follows instructions better than 4o-mini).
  `gpt-4.1` if tickets feel flat. Claude (Haiku 4.5) is worth trying after the event, since it
  needs a second provider in `ai_client.py`. Confirm the model is listed on the account.
- **"Should I leave my partner":** relationship questions get a hedge, not a verdict.
- **Cubs versus Sox:** Narly likes both but favors the Sox, because bears (and cubs) eat fish.
- **Birthday:** Narly turns 2; he was created at the 2024 US Festival.

## Open questions for /spec
- Does the question echo stay within the length limit? Check on the replay set.
- Does the prompt inference catch "Umbraco" mishearings? Add "Umbraco" clips to the replay set in
  `_work/live-baseline/`.
- Hedge rate on the replay set: is a prompt rule enough, or is code rationing needed after all?
