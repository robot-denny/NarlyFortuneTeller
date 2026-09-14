# Performance review — project rules

This is a single-user physical installation, not a service. Throughput, N+1 queries, payload
size, caching layers and bundle weight do not apply — **do not report them.**

What matters is latency and liveness in one guest interaction, coin to printed slip:

- **Blocking the serial loop.** `serial_trigger.py` must keep reading `COIN X` messages. Long
  synchronous work on that loop means a coin inserted during a fortune is dropped.
- **Startup-cached work must stay cached.** `init_ai(persona)` and `load_config(persona)` run
  once at startup by design. Moving either into the per-coin path adds file I/O and client
  construction to every interaction.
- **Timeouts are the real budget.** Mic, OpenAI and printer calls each have one. A change that
  lengthens or removes a timeout trades a hang for a wait — the machine has no operator.
- **Token and length settings are cost and latency.** `max_tokens` and max-character settings in
  the persona configs have been tuned repeatedly in history. Flag changes that raise them
  without a stated reason.
- **The Arduino drives animations locally, on purpose.** LED timing lives in the sketch so it
  stays smooth regardless of what Python is doing. A change that drives per-frame animation over
  serial from Python is a regression.
