# Prompt Revision Log

Every edit to `prompts.py` gets an entry here **at the same moment the edit is
made** (`CURSOR_INSTRUCTIONS.md` §5) — not written up afterward. `prompts.py`
doesn't exist yet (it lands in Phase 5, ReAct agent loop + system prompt), so
there's nothing to log yet. This file is initialized now so the format is
fixed before the first real prompt is written.

## Entry format

```
## <YYYY-MM-DD> — <short title of what changed>
**Trigger:** <the specific failure or gap observed — a transcript excerpt,
  a failing test, or a behaviour that violated an SRS requirement>
**Before:**
> <the exact prior prompt text, or the relevant excerpt>
**After:**
> <the exact new prompt text>
**Why this fixes it:** <1-3 sentences, tie back to the SRS requirement or
  design principle (P1-P7) it restores>
```

Do not summarize a diff instead of quoting it — the before/after text is what
makes this file useful in a live walkthrough; a paraphrase isn't verifiable
against `prompts.py`'s actual history.

---

*(No entries yet — `prompts.py` is written in Phase 5.)*
