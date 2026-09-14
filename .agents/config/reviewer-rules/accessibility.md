# Accessibility review — project rules

**This project has no graphical user interface.** There is no HTML, no web framework, no
components, no DOM, no client-side code. WCAG criteria, semantic markup, ARIA, focus management
and keyboard navigation have nothing to apply to — **do not report findings in those
categories, and do not infer a UI that does not exist.**

The project's interface is physical and its accessibility concerns are real but different. Where
a diff touches them, they are worth raising:

- **The printed ticket is the entire output.** `formatters.py` wraps to 32 characters on a 58mm
  thermal printer. Cramped spacing, lost line breaks, or dropped non-ASCII characters make a
  fortune unreadable — special-character handling has already broken once (`9e2fec0`).
- **Audio cues carry state.** The SFX in `sfx/` tell a guest when Narly is listening and when he
  is thinking. Removing or silencing a cue leaves a guest with no signal to speak. Phase 4's
  QUIET mode deliberately skips them — in that mode the LEDs are the only feedback.
- **LED animations are the other state channel**, and are the only feedback available to a guest
  who cannot hear the cues. Colour alone distinguishes several Phase 4 states; animation
  *motion* differing per state (breathe, twinkle, solid, sparkle, chase) is what keeps them
  distinguishable, so preserve that distinction rather than collapsing states to colour.
- **Speech is the only input.** A guest who cannot speak, or is not understood, must still get a
  slip — the fallback path is an accessibility feature, not just error handling.
