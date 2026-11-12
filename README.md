# Flutter App Store Review Pre-flight

**flutter-app-store-review** gives Claude Code (and other coding agents) the
App Store reviewer's checklist before you submit. It scans a Flutter project
and reports everything Apple will reject:
- missing Sign in with Apple
- required profile fields Apple says you don't need
- vague permission strings
- broken subscription flows
- missing EULA and privacy links
- payment frameworks linked into the app but never used
- an ATT prompt that never shows
- personal data sent to AI services without the user's consent

It also reads your privacy policy, compares it with what your app actually
collects, and writes the missing sections for you.

It is one skill, written in Markdown, with a Python scanner that needs no
installs. Free, MIT license.

I'm [Ben Mukanirwa](https://x.com/benmukanirwa), co-founder of
[Pikelo](https://www.linkedin.com/company/pikelo/), an English learning app
for French speakers. Getting our Flutter app through App Review took almost
**two years** of back-and-forth: more than a dozen rejection rounds covering
login, subscriptions, privacy, iPad and AI disclosure. Every one of those
rejections is now a rule in this skill. The reviewer's wording, the real cause
and the fix that actually worked are all in it, so you don't have to learn them
the way we did.

Fork it. Improve it. Add your own rejections. If it saves you even one
rejection round, it did its job.

## Who this is for

- **Flutter developers shipping to iOS for the first time.** Know what App
  Review checks before you get the email.
- **Teams stuck in a rejection loop.** Find *every* issue in one pass, instead
  of fixing one per round.
- **Founders with subscription apps.** In-app purchases, paywalls and App Store
  Connect setup are where most rejections happen.

## What it does

- **Finds what the reviewer will find.** It covers 24 rules built from real
  rejections:
  - Guideline 2.1: app completeness and missing information
  - Guidelines 2.3.2 and 2.3.3: accurate metadata
  - Guidelines 3.1.1 and 3.1.2(c): payments and subscriptions
  - Guidelines 4 and 4.8: design and login services
  - Guidelines 5.1.1 and 5.1.2: privacy, data collection and data use
- **Knows what kind of app you have.** It detects your subscription stack
  (`in_app_purchase`, RevenueCat, Adapty, and others), your login providers,
  AI services, tracking SDKs and iPad support. Subscription checks run only
  when you actually sell something.
- **Fixes your privacy policy.** It fetches your policy URL and maps your SDKs,
  permissions and form fields to Apple's App Privacy categories. It then lists
  the gaps and gives you ready-to-paste sections, plus your App Store Connect
  privacy answers.
- **Writes your App Store Connect text.** Review Notes, demo account notes,
  replies to the reviewer, and the subscription text for your App Description.
- **Fixes code with your approval.** You get a report first. It only edits code
  after you say yes.

## Install

### Claude Code: `git clone` (recommended)

For all your projects:

```bash
git clone https://github.com/BenCodeurr/flutter-app-store-review.git ~/.claude/skills/flutter-app-store-review
```

For one project only, run this from your Flutter app's root:

```bash
git clone https://github.com/BenCodeurr/flutter-app-store-review.git .claude/skills/flutter-app-store-review
```

Then open Claude Code in your Flutter project and ask:

> Run the App Store review pre-flight on this app.

To update later:

```bash
git -C ~/.claude/skills/flutter-app-store-review pull
```

### Other agents (Codex, Cursor, Gemini CLI…)

Clone the repo anywhere and tell the agent to follow
`flutter-app-store-review/SKILL.md`. Or copy it into the agent's own skills or
rules folder.

### Scanner only (no agent, or in CI)

```bash
python3 ~/.claude/skills/flutter-app-store-review/scripts/scan.py path/to/flutter_app
```

To also inspect the built binary and save JSON results:

```bash
python3 ~/.claude/skills/flutter-app-store-review/scripts/scan.py path/to/flutter_app --app build/ios/ipa/App.ipa --json scan.json
```

- Needs Python 3.8+ and the standard library only.
- `--app` runs `otool` on the built binary (macOS) to show exactly which
  frameworks Apple sees.
- The scanner exits with code `1` when it finds any BLOCKER, so you can fail a
  CI job on it.

## What it checks

| Area | Guidelines |
|---|---|
| Sign in with Apple required alongside social login; entitlement; button design; Apple sends the email only on first sign-in; Google URL scheme | 4.8, 4, 2.1(a) |
| Required personal fields (country, city, job, phone…) | 5.1.1(v) |
| Vague, missing or unused `Info.plist` purpose strings | 5.1.1(ii) |
| Personal data sent to a third-party AI service without in-app consent (from the app **or** the backend) | 5.1.1(i), 5.1.2(i) |
| Web/Stripe payments and promo codes for digital content | 3.1.1 |
| Paywall: EULA + privacy links, price, period, restore; EULA in metadata | 3.1.2(c) |
| IAP errors in review: product handling, unfinished transactions, sandbox receipts, Paid Apps Agreement, products not submitted | 2.1(b) |
| Paywall forcing Sign in with Apple | 2.1(a) |
| PassKit / ProximityReader / ATT linked but unused | 2.1 Information Needed |
| ATT prompt not showing (requested too early) | 2.1 |
| iPad: grey screens, orientations, real iPad screenshots | 2.1(a), 2.3.3 |
| Privacy manifest, account deletion, privacy link in app | 5.1.1 |
| Demo accounts (TestFlight **and** App Store, expired subscription) | 2.1 |
| Promoted IAP images and names | 2.3.2 |

## Layout

```
SKILL.md                     agent workflow
scripts/scan.py              static scanner
references/rules.md          every rule: reviewer wording, causes, fixes, manual checklist
references/subscriptions.md  full IAP / subscription checklist
references/privacy-policy.md policy gap analysis + App Privacy mapping
references/asc-templates.md  Review Notes and reply templates
```

## Limitations

- The scanner pattern-matches source code, so `REVIEW` findings need a person
  or agent to confirm them.
- It can't see your backend, App Store Connect or screenshots. The skill asks
  you about those instead.
- No tool can guarantee approval. This one removes the rejection causes we
  know about.

## Contributing

Got a rejection that isn't covered? That's the most valuable contribution
there is. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
