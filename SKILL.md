---
name: flutter-app-store-review
description: Audit a Flutter project for Apple App Store / TestFlight review rejections before submitting. Detects whether the app has subscriptions/IAP, third-party login, AI services, tracking and iPad support, then checks Info.plist purpose strings, Sign in with Apple, required profile fields, paywall requirements (EULA/privacy/restore), external payments and promo codes, unused PassKit/ProximityReader/ATT frameworks, privacy manifest, account deletion and third-party AI data sharing. Fetches the user's privacy policy and proposes updates matching what the app actually collects, and drafts App Store Connect review notes. Use when the user mentions App Store review, TestFlight review, App Review rejection, a guideline number (2.1, 2.3.3, 3.1.1, 3.1.2, 4.8, 5.1.1, 5.1.2), "get my Flutter app approved", or is preparing an iOS submission.
---

# Flutter App Store Review Pre-flight

This skill was built from a real two-year history of App Review rejections for a
Flutter app with subscriptions, Sign in with Apple + Google, profile onboarding,
microphone recording and an AI feature. Every rule in `references/rules.md` is
tagged with whether it came from that real history (`[seen]`) or is a common
rejection worth checking anyway (`[common]`).

The goal: find **everything** a reviewer will hit in one pass, so the app is
approved on the first or second submission instead of the tenth.

## Key facts learned the hard way

- **Apple reviews on iPad.** Every review in the source history ran on an iPad
  (Air / Pro, latest iPadOS), even for a phone-first app. iPhone-only apps are
  still tested on iPad in compatibility mode. Test every flow on an iPad
  simulator in **release mode** on a **fresh install**.
- Reviewers repeat the **same** rejection until *every* item in it is fixed.
  Fix all items, then reply in App Store Connect explaining each fix.
- Many rejections are **App Store Connect configuration**, not code (IAPs not
  submitted, Paid Apps Agreement, EULA link in description, screenshots).
  The skill must cover both.

## Workflow

Follow these steps in order. Do not edit any file until step 6.

### Step 1 — Run the scanner

```bash
python3 <skill_dir>/scripts/scan.py <flutter_project_root> --json /tmp/review-scan.json
```

Optional, if the user has a built app (most accurate for linked frameworks):

```bash
flutter build ipa --release   # or use an existing .ipa / Runner.app
python3 <skill_dir>/scripts/scan.py <root> --app build/ios/ipa/<App>.ipa
```

The scanner prints an **App profile** (subscriptions? login providers? AI?
tracking? iPad?) and findings with rule IDs (`R01`…). It is heuristic: treat
`REVIEW` findings as "open the file and confirm", not as facts.

### Step 2 — Confirm the app profile with the user

The profile decides which rule sets apply. Ask the user to confirm or correct
it with AskUserQuestion (one batch). Ask only what the scanner could not
determine:

1. **Monetization**: auto-renewable subscriptions / one-time IAP / paid app /
   free with no purchases / physical goods or services (Apple Pay/Stripe is
   allowed for those). Does any *digital* content get unlocked by a web
   payment, promo code or referral code?
2. **Accounts**: is login required? Which providers? Is there a guest mode?
   Does purchasing require an account, and why?
3. **Backend AI / data sharing**: does the *backend* (not only the app) send
   user content to OpenAI, Gemini, Anthropic, ElevenLabs, Deepgram, etc.?
   The scanner can't see server code.
4. **Tracking**: does the app or any SDK link user data with third-party data
   for ads, or share it with data brokers? (If not, App Privacy must not
   declare tracking, and the ATT prompt should be removed.)
5. **iPad**: intentionally supported, or iPhone-only?
6. **Privacy policy URL** and **Terms of Use URL** (or "using Apple's standard
   EULA"). Always ask for these — step 4 needs them.

If the app has **no subscriptions/IAP**, skip the subscription rules
(R09–R13, `references/subscriptions.md`) except R09 (external payment for
digital goods is still forbidden).

### Step 3 — Verify findings and run manual checks

1. Open each `HIGH`/`BLOCKER`/`REVIEW` finding's file and confirm it. Drop
   false positives and say why.
2. Read `references/rules.md` for every rule that fired — it has the exact
   reviewer wording, root causes and fixes.
3. If the app has subscriptions, read `references/subscriptions.md` and walk
   the full IAP checklist (code + App Store Connect + sandbox testing). The
   "IAP shows an error" rejection repeated four times in the source history.
4. Go through the **Manual checklist** in `references/rules.md` (screenshots,
   demo accounts, promotional images, Paid Apps Agreement) and ask the user
   about each item that can't be checked from code.

### Step 4 — Privacy policy comparison

Follow `references/privacy-policy.md`:

1. Fetch the privacy policy URL (WebFetch). If it fails or is behind JS,
   ask the user to paste the text.
2. Build the **data inventory** from the scanner JSON (`data_inventory`,
   `third_parties`, `permissions`, `form_fields`, `ai_services`) plus the
   user's answers about the backend.
3. Produce a gap table: each data type / third party / purpose the app has
   vs. whether the policy covers it.
4. Propose **ready-to-paste policy sections** for every gap, in the policy's
   own language and tone.
5. Draft the **App Store Connect → App Privacy** answers (data types, linked
   to user?, used for tracking?) so they match the code and the policy.

Never invent data practices. If something is unknown, mark it
`[CONFIRM: …]` in the draft.

### Step 5 — Report

Write `APP_REVIEW_REPORT.md` in the project root with:

1. **App profile** (confirmed).
2. **Blockers / High / Medium / Info** findings, each with guideline number,
   `file:line`, what the reviewer would say, and the fix.
3. **App Store Connect actions** (things outside the code), as a checklist.
4. **Privacy policy gap table** and proposed sections.
5. **App Privacy (nutrition label) answers.**
6. **Review Notes draft** and any reply-to-reviewer drafts, from
   `references/asc-templates.md`, filled in with the app's real details.

Then summarize the top issues to the user in chat.

### Step 6 — Offer fixes

Ask the user which fixes to apply (AskUserQuestion, multiSelect). Only then
edit code. Safe, mechanical fixes you can offer:

- Rewrite vague `NS*UsageDescription` strings (purpose + concrete example).
- Add missing usage-description keys for plugins that need them.
- Remove unused usage-description keys (e.g. `NSUserTrackingUsageDescription`
  when nothing tracks).
- Make non-essential profile fields optional (remove `validator` errors, add
  "(optional)" to labels) — keep server-side validation in sync; warn the
  user the backend may reject empty values.
- Add Terms of Use + Privacy Policy links, price, period and Restore button to
  the paywall.
- Add a third-party AI consent screen (see R16 in `rules.md`).
- Add `PrivacyInfo.xcprivacy`.
- Move the ATT request to after the first frame / app active.
- Use the official `SignInWithAppleButton` with equal sizing to other login
  buttons.

After editing, re-run the scanner and show the before/after counts.

## Rules

- Never claim the app "will pass". Say which known rejection causes were
  checked and which remain manual.
- Never edit App Store Connect yourself or reply to Apple for the user; draft
  text for them to paste.
- Don't put secrets (demo passwords) into files committed to git. Put them in
  the report only if the user asks, and remind them to not commit it.
- Quote the guideline numbers exactly as listed in `rules.md`.
