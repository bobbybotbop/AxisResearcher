# Link the title-simplification prompt for Copy Seller

Type: task
Status: open

## Summary

The Copy Seller research pipeline needs to reduce a seller's listing title to a
short, common search phrase (too specific a search returns no results). This is
NOT the same as the existing Title Search Pipeline's Claude Haiku trim prompt
(`prompts/trimTitlePrompt.txt`) — the user confirmed it is a different prompt.

The prompt will be authored by a separate agent later. This ticket tracks linking
that prompt into the Copy Seller pipeline once it is ready.

## Blocked by

External: the title-simplification prompt, to be produced by a different agent.

## When unblocked

- Add the prompt file under `prompts/` (follow existing naming convention).
- Wire it into the Copy Seller pipeline's "simplify title → search phrase" step.
- Expose the prompt as an editable field in the Testing tab (per the Testing Tab
  Philosophy: nothing hidden).

## Comments
