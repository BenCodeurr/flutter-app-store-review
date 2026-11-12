# Contributing

Thanks for helping other Flutter developers get through App Review faster.
The skill is only as good as the rejections it knows about, so **real
rejections are the most valuable contribution.**

## Ways to contribute

1. **Add a rejection you received**: a new rule, or new causes and fixes for
   an existing rule.
2. **Improve the scanner** (`scripts/scan.py`): new packages, fewer false
   positives, new detections.
3. **Fix outdated guidance.** Apple changes guidelines and App Store Connect
   often. If something here is no longer true, open an issue or PR with a link
   to the source.
4. **Report a false positive or false negative.** Open an issue with a minimal
   code snippet (no secrets) and the scanner output.

## Adding a rejection

Open an issue or PR with:

- **Guideline**: exactly as Apple wrote it, e.g. `Guideline 2.1(b) - Performance - App Completeness`.
- **Reviewer message**: the relevant part of Apple's text. Remove your app
  name, product names, submission IDs, people's names and anything private.
- **Review device / OS**, if given (e.g. iPad Air 11-inch (M3), iPadOS 26.5).
- **Root cause**: what was actually wrong in your app or App Store Connect.
- **What fixed it**: the code change, setting or reply that got it approved.
  Say if you're not sure which change did it.
- **How to detect it**: a package, file, `Info.plist` key or code pattern the
  scanner could look for, if there is one.

Then in `references/rules.md`:

- Add it under the right section. Tag it `[seen]` if you got this rejection
  yourself, or `[common]` if it's well known but not from your own history.
- Use the next free rule ID (`R25`, `R26`, …) and don't renumber existing
  ones, since the scanner output refers to them.
- If it's about subscriptions or IAP, also update `references/subscriptions.md`.
- If it affects the privacy policy or App Privacy answers, also update
  `references/privacy-policy.md`.

## Changing the scanner

- **Standard library only.** No `pip install`. The scanner has to run anywhere
  `python3` exists.
- **Use the right severity:**
  - `BLOCKER`: near-certain rejection.
  - `HIGH`: likely rejection.
  - `MEDIUM`: should fix.
  - `REVIEW`: heuristic that needs a human to confirm.
  - `INFO`: advice.
  - When unsure, use `REVIEW`.
- Each finding needs a rule ID that exists in `rules.md`, the guideline number,
  and a `file:line` when possible.
- Test against a small fixture project with the problem, and one without it, to
  check there's no false positive:

  ```bash
  python3 scripts/scan.py path/to/fixture
  python3 scripts/scan.py path/to/fixture --json out.json
  ```

- Put the before/after output in your PR description.

## Changing SKILL.md

Keep it short and procedural. `SKILL.md` says *what to do in which order*; the
details belong in `references/`. The agent must still ask before editing user
code, and must never act in App Store Connect on the user's behalf.

## Pull requests

- One topic per PR.
- Never include real credentials, demo account passwords, bundle IDs or private
  app details.
- By contributing, you agree your contribution is licensed under the MIT
  License of this repository.

## Code of conduct

Be kind and specific. Everyone here has been rejected by App Review at least
once.
