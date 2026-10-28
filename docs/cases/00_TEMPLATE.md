# Case `<CASE_ID>`, `<short human name>`

> Copy this file to `docs/cases/<category>/<case-id>.md`, one per case. Keep it short and concrete.
> ChargeCascade's per-case pages are the reference for depth. Delete this quote block on use.

- **Category:** `<category>` (the domain problem-type it represents)
- **Source:** synthetic (with sim knobs) | real sample (which datum) | uploaded
- **One line:** what this case is, in a sentence.

## Why this case exists

Which coverage axis it occupies, or which negative/sanity control it is. State plainly if it is a
decoy or a degenerate control (for example: empty input must not crash; a non-failing scene the
detector must NOT alarm on). A deck without explicit controls is incomplete.

## Formalization

The parameters, the seed, and the inputs that define the case. Enough that a reader can regenerate
it. Reference the engine/stage that consumes them.

| Parameter | Value | Meaning |
|---|---|---|
| `<param>` | `<value>` | `<what it sets>` |

## Expected results

What a domain expert should see, qualitatively and quantitatively. This is the **expected band**
surfaced on the case chip. Be specific about magnitude and shape, not just "it works".

## Validation anchor

The independent check this case is measured against: a published number, a closed-form value, a
conservation law, or a control outcome. State the tolerance. If the engine output contradicts the
anchor, that is a defect to report, not to hide.

## Notes

Outlier policy, caveats, known limitations, and any data-provenance or license note for a real sample.
