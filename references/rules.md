# Rules catalog

Each rule: ID (matches scanner output), guideline, origin tag, what the reviewer
says, root causes in Flutter apps, how to detect, how to fix.

- `[seen]` = this exact rejection happened in the source history (often more than once).
- `[common]` = not in the source history, but a frequent rejection worth checking.

Severity used by the scanner: `BLOCKER` (near-certain rejection), `HIGH`,
`MEDIUM`, `REVIEW` (heuristic, confirm by reading code), `INFO`.

---

## Login and accounts

### R01 — Third-party login without Sign in with Apple · 4.8 `[seen]`

> "The app uses a third-party login service, but does not appear to offer an
> equivalent login option with the following features: limits data collection
> to the user's name and email address; allows users to keep their email
> address private; does not collect interactions with the app for advertising
> purposes without consent."

- **Detect**: `google_sign_in`, `flutter_facebook_auth`, `twitter_login`,
  `flutter_line_sdk`, `firebase_ui_oauth_*`, `supabase` OAuth with Google etc.,
  and no `sign_in_with_apple` (or `firebase_auth` `AppleAuthProvider`) usage.
- **Fix**: add Sign in with Apple (`sign_in_with_apple` package or
  `FirebaseAuth.instance.signInWithProvider(AppleAuthProvider())`). Email/password
  or phone login alone does *not* trigger 4.8, but any social login does.
- Also update screenshots if they show the login screen.

### R02 — Sign in with Apple capability missing · 2.1(a) `[seen]`

> "The app produced an error during our attempt to create an account with Sign in
> with Apple." / "we were unable to login using Sign in with Apple and Google."

Common Flutter causes (check all):
1. `ios/Runner/Runner.entitlements` lacks
   `com.apple.developer.applesignin` = `[Default]`, or the entitlements file is
   not referenced by `CODE_SIGN_ENTITLEMENTS` for **Release**.
2. App ID in the Developer portal doesn't have Sign in with Apple enabled →
   regenerate provisioning profile.
3. Backend expects `email`/`fullName` on every login. Apple sends them **only
   the first time** a user authorizes the app. Reviewers often use an Apple ID
   that already authorized it → backend crashes on null email. Store the Apple
   `sub` (user identifier) as the key; treat email/name as optional.
4. Firebase: raw nonce/hashed nonce mismatch (pass SHA-256 of the nonce to Apple,
   the raw nonce to Firebase), or Apple provider not enabled in Firebase console.
5. Backend validates the identity token `aud` against the wrong value (must be the
   **bundle ID** for native iOS; the Service ID only for web/Android).
6. Private relay emails (`@privaterelay.appleid.com`) rejected by an email
   validator or treated as duplicates.
7. Error surfaced as a generic "Something went wrong" — always show a
   meaningful message and log the actual error.

Google Sign-In failing on iPad: missing `GIDClientID` and the
`REVERSED_CLIENT_ID` URL scheme in `Info.plist` (scanner R04), or the iOS client
ID not matching the bundle ID.

### R03 — Sign in with Apple button not equivalent · 4 (Design) `[seen]`

> "Sign in with Apple is not displayed in the app as an equivalent option for
> logging in… It is not clear that the Sign in with Apple button is a button,
> because it does not have a border."

- **Detect**: `sign_in_with_apple` is used but no `SignInWithAppleButton`
  widget (custom button) — confirm visually.
- **Fix**: use `SignInWithAppleButton` (or follow the HIG exactly: Apple logo,
  "Sign in with Apple"/"Continue with Apple", black / white / white-outlined
  style). Same width, height, corner radius and prominence as the Google button,
  and place it **first or equal** to other providers. On a white background use
  the black style or the white style **with outline**.

### R04 — Google Sign-In URL scheme missing · 2.1(a) `[seen]`

- **Detect**: `google_sign_in` in deps; `Info.plist` has no `CFBundleURLTypes`
  entry starting with `com.googleusercontent.apps.`.
- **Fix**: add `GIDClientID` and the reversed client ID URL scheme from
  `GoogleService-Info.plist`.

### R19 — No in-app account deletion · 5.1.1(v) `[common]`

- **Detect**: account creation exists (auth packages / sign-up screens) and no
  "delete account" text in `lib/`.
- **Fix**: add a clearly findable "Delete account" in settings that deletes the
  account (not just deactivates) — or starts deletion and explains the timeline.
  If the user signed in with Apple, revoke the token via the Sign in with Apple
  REST API. Tell users that deleting the account doesn't cancel an App Store
  subscription, and link to Manage Subscriptions.

### R22 — Demo account / login the reviewer can't pass · 2.1 Information Needed `[seen]`

> "We were unable to sign in with the demo account credentials you provided…"
> "We suggest that you implement a bypass or guest option for the TestFlight
> submission." "We need access to a demo account with an expired subscription to
> review the entire purchase flow."

Causes: OTP / SMS / email-magic-link login (reviewer can't receive it),
2FA, region-locked phone numbers, demo account deleted/reset by a backend job,
account already subscribed, credentials entered only for the App Store version
but not for **TestFlight → Test Information → Beta App Review Information**
(they are separate).

Fix:
- Provide a username + password demo account in **both** App Review Information
  (App Store) and Beta App Review Information (TestFlight). Tick "Sign-in required".
- If login is OTP-only, whitelist the demo phone/email with a fixed code and
  write the code in Review Notes.
- For subscription apps provide a demo account **without an active
  subscription** (never subscribed or expired) so the reviewer can buy in
  sandbox. Optionally a second account with an active subscription.
- Make sure the demo account skips/completes onboarding and doesn't hit a
  required field the reviewer can't fill.
- Protect the demo account from cleanup scripts; test it the day you submit.

---

## Personal data and privacy

### R05 — Required personal info not needed for core function · 5.1.1(v) `[seen ×4]`

> "The app requires users to provide personal information that is not directly
> relevant to the app's core functionality… Update the app to not require users
> to provide: Country, Job, Phone number" … later "Country of origin,
> Occupation" … later "City/country".

This came back four times because each round only some fields were fixed.
**Audit every** sign-up / onboarding / profile-completion form at once.

- **Detect**: form fields labeled country, city, nationality, occupation, job,
  profession, company, phone, gender, date of birth/age, address, marital status,
  income, with a `validator` that returns an error when empty, or a disabled
  Continue button until filled.
- **Fix**: make them optional (label "(optional)", no empty-value validation,
  backend accepts null), or remove them. Only keep a field required if the core
  feature cannot work without it, and be ready to explain why in Review Notes
  (e.g. age gate required by law). Also check the **backend** doesn't reject
  empty values — a reviewer skipping an optional field and then getting an
  "unidentified error" is a 2.1(a) rejection (also seen).

### R06 / R07 / R08 — Purpose strings · 5.1.1(ii) `[seen]`

> "Update the microphone purpose string to explain how the app will use the
> requested information and provide a specific example of how the data will be
> used." Bad examples: "App needs microphone access".

- **R06 missing**: a plugin needs a key that `Info.plist` lacks → crash on
  request (2.1 bug) or binary rejection.
- **R07 vague**: shorter than ~40 chars, generic ("needs access", "would like
  to access", "for app functionality"), no concrete example.
- **R08 unused**: key present but no plugin uses it — reviewer will look for the
  feature. Remove it (especially `NSUserTrackingUsageDescription`, location,
  contacts).

Template: **"<App> uses the <resource> to <purpose>. For example, <concrete
user-visible example>."**

Good: "StudyBuddy uses the microphone to record your spoken answers during practice
sessions. For example, when you tap Record on a question, your answer is
recorded so you can play it back and get feedback."

Localize purpose strings (`InfoPlist.strings`) if the app is localized.

### R16 — Personal data sent to a third-party AI service · 5.1.1(i) + 5.1.2(i) `[seen]`

> "The app appears to share the user's personal data with a third-party AI
> service but the app does not clearly explain what data is sent, identify who
> the data is sent to, and ask the user's permission before sharing the data…
> Note that only including this information in the app's Terms of Service or
> Privacy Policy is not sufficient."

Applies even when the AI call happens on **your backend** (e.g. audio answers
transcribed by Whisper, text scored by GPT/Gemini).

- **Detect**: packages `google_generative_ai`, `firebase_ai`,
  `firebase_vertexai`, `dart_openai`, `openai_dart`, `langchain*`,
  `anthropic_sdk_dart`, `mistralai_dart`, `ollama_dart`, `chat_gpt_sdk`,
  `elevenlabs*`, `deepgram*`; hostnames `api.openai.com`,
  `generativelanguage.googleapis.com`, `aiplatform.googleapis.com`,
  `api.anthropic.com`, `api.mistral.ai`, `api.groq.com`, `openrouter.ai`,
  `api.elevenlabs.io`, `api.deepgram.com`, `api.assemblyai.com`,
  `api.together.xyz`, `api.replicate.com`. Plus ask the user about the backend.
- **Fix** (all of these):
  1. Before the **first** AI feature use, show an in-app consent screen/sheet:
     - what data is sent ("your recorded audio answers and the question text"),
     - who receives it, **by name** ("OpenAI, L.L.C.", "Google (Gemini)"),
     - why, and whether it's used to train models,
     - buttons **Allow** / **Not now**. Declining must keep the rest of the app
       usable (disable just the AI feature).
  2. Store the consent (with version); allow revoking in Settings.
  3. Don't send data before consent — including background/prefetch calls.
  4. Update the privacy policy with the same details (see `privacy-policy.md`).
  5. Update App Privacy in App Store Connect (e.g. Audio Data / Other User
     Content collected, App Functionality).
  6. In Review Notes, say where the consent screen is and attach a recording.
- If the app truly doesn't send data to AI, reply saying so and add it to Review
  Notes.

### R17 — Privacy manifest missing · 5.1.1 / ITMS-91053 `[common]`

- **Detect**: no `ios/Runner/PrivacyInfo.xcprivacy`.
- **Fix**: add one declaring Required Reason APIs used by your own code and
  plugins without their own manifest (`shared_preferences` → UserDefaults
  `CA92.1`; file timestamps `C617.1`; disk space `E174.1`; system boot time
  `35F9.1`), `NSPrivacyTracking`, and `NSPrivacyCollectedDataTypes`. Add it to
  the Runner target in Xcode. Update plugins — most popular ones ship manifests now.

### R21 — No privacy policy link inside the app · 5.1.1(i) `[common]`

- **Detect**: no `privacy` URL in `lib/`.
- **Fix**: link the policy from Settings/About and from the sign-up and paywall
  screens. The App Store Connect Privacy Policy URL field must also be filled.

---

## Payments and subscriptions

See `subscriptions.md` for the full IAP checklist.

### R09 — Digital content purchasable outside IAP · 3.1.1 `[seen]`

> "The app allows users to purchase subscriptions natively or via a web view in
> the app using payment mechanisms other than in-app purchase."

- **Detect**: `flutter_stripe`, `stripe_*`, `flutter_paystack`, `flutterwave*`,
  `razorpay_flutter`, `paypal*`, `square_*`, `pay` package; `webview_flutter`
  /`url_launcher`/`flutter_inappwebview` opening URLs with
  checkout|payment|billing|pricing|subscribe|stripe|paystack|paypal.
- **Fix**: on iOS, sell digital subscriptions/content only via StoreKit
  (`in_app_purchase`, RevenueCat…). Gate the web checkout with
  `Platform.isIOS`. Physical goods and real-world services may use
  Stripe/Apple Pay. US storefront: external purchase links are allowed under the
  2025 rules, but buying *inside* the app still must be IAP — when unsure, hide
  the web option on iOS entirely.

### R10 — Promo/referral codes unlock subscriptions · 3.1.1 `[seen]`

> "The app still uses promo codes to unlock the subscriptions… use an
> Apple-supported offer code."

- **Detect**: text "promo code", "coupon", "voucher", "redeem code",
  "referral code", "activation code", "gift code" in `lib/`.
- **Fix**: remove the custom code field on iOS. Use App Store **offer codes**:
  `InAppPurchaseStoreKitPlatformAddition().presentCodeRedemptionSheet()`
  (`in_app_purchase_storekit`) or `Purchases.presentCodeRedemptionSheet()`
  (RevenueCat). Referral rewards can't unlock paid features on iOS unless
  delivered as an Apple offer code.

### R11 — Paywall missing required info · 3.1.2(c) `[seen ×3]`

> "The following information needs to be included within the app: a functional
> link to the Terms of Use (EULA) and a functional link to the privacy policy…
> [and] in the App Store metadata: a functional link to the Terms of Use (EULA)."

Required **in the app**, on/near the purchase screen:
- Subscription title, length (e.g. "1 month"), price (from StoreKit, localized
  — never hardcoded), price per unit if showing a discount ("€4.99/month,
  billed €59.88 yearly").
- Tappable **Terms of Use (EULA)** and **Privacy Policy** links.
- **Restore Purchases** button `[common]`.
- Free trial: what is charged and when after the trial ends.

Required **in App Store Connect** (this one was missed twice — it's a metadata
fix, not a binary fix):
- Privacy Policy URL field.
- Terms of Use: if using Apple's standard EULA, add a line to the **App
  Description**: `Terms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`.
  If custom, add it under App Information → License Agreement.

### R12 — IAP flow shows an error · 2.1(b) `[seen ×4]`

> "The In-App Purchase products in the app exhibited one or more bugs… an error
> message appeared after trying to purchase."

See `subscriptions.md` → "Why the purchase fails in review". Scanner flags
product queries that don't handle missing products.

### R13 — Paywall forces (re)login / Sign in with Apple · 2.1(a)/2.1(b), 5.1.1(v) `[seen ×2]`

> "Attempting to initiate the In App purchase flow redirected to the Sign in
> with Apple login mechanism." / "We were asked to Sign in with Apple when in my
> subscription page."

Causes: purchase code calls a "link account"/re-auth step; the session token
expired / wasn't persisted (reviewer logged in with demo account but the app
still thinks they're a guest); paywall route guarded by "isAppleUser".

Fix: if the user is logged in, never prompt again — purchase directly. If the
app allows guests, either let guests buy (attach the purchase to an anonymous
ID, e.g. RevenueCat anonymous user, and transfer on login) or show a clear
explanation *before* the paywall that an account is needed to sync the
subscription, with all login options (not only Apple).

### R23 — IAP products not submitted · 2.1(b) `[seen ×2]`

> "The app includes references to subscriptions but the associated In-App
> Purchase products have not been submitted for review… you must provide an App
> Review screenshot."

App Store Connect only. See `subscriptions.md` → App Store Connect checklist.

### R24 — Promotional IAP image/name issues · 2.3.2 `[seen]`

> "The Image for your promoted In-App Purchase… includes references to the price."
> "Your promotional image is a screenshot taken from the app… includes text
> that is small or otherwise hard to read."

Manual: promoted IAP images (1024×1024) must be unique artwork (not an app
screenshot), no price, no small text. Display name ≤ 30 chars, description ≤ 45,
no price. If not promoting, delete the promo image.

---

## Frameworks the reviewer sees in the binary

### R14 — PassKit / ProximityReader linked but unused · 2.1 Information Needed `[seen ×2]`

> "The app binary includes the ProximityReader framework for implementing Tap to
> Pay, but we were unable to verify any integration." / same for PassKit /
> Apple Pay.

- **Detect**: pods `Stripe`, `StripeApplePay`, `StripePaymentSheet`,
  `StripeTerminal` (ProximityReader), Flutter `pay`, `flutter_stripe`,
  `mek_stripe_terminal`, `square_*`; or `otool -L` on the built binary
  (`--app`).
- **Fix**: remove the SDK from iOS builds if unused (after removing
  `flutter_stripe` for R09, run `cd ios && pod deintegrate && pod install` and
  confirm with `otool`). If used for physical goods, say where in Review Notes.
  If you must keep it, add to Review Notes: "The app does not use Apple Pay /
  Tap to Pay. PassKit is linked by <SDK> used for <purpose>."

### R15 — ATT framework present but prompt not shown · 2.1 Information Needed `[seen]`

> "The app uses the AppTrackingTransparency framework, but we are unable to
> locate the App Tracking Transparency permission request when reviewed on iPadOS…"

Two separate decisions:
1. **Do you track?** (link data with third parties for ads/measurement, or
   share with data brokers — e.g. Facebook App Events, AppsFlyer, Adjust,
   AdMob personalized ads.) If **no**: remove `app_tracking_transparency`,
   remove `NSUserTrackingUsageDescription`, set App Privacy "Used for tracking"
   to **No** for every data type, and say so in Review Notes.
2. If **yes**, the prompt must appear **before** any tracking data is collected.
   Common Flutter bug: `requestTrackingAuthorization()` called in `main()` or
   `initState` of the first screen before the app is active → on recent iOS it
   returns `notDetermined` silently and no dialog appears. Fix: call it after
   the first frame **and** when `AppLifecycleState.resumed`, with a short delay;
   initialize ad/attribution SDKs only after the result. Provide a screen
   recording from a fresh install in Review Notes.

---

## Stability, iPad and metadata

### R18 — iPad supported: layout, screenshots, orientations · 2.1(a), 2.3.3 `[seen]`

> "Your app displayed a grey screen in the home page and the profile page."
> (iPad Air) / "The 13-inch iPad screenshots still show an iPhone image that has
> been modified or stretched."

- **Grey screen** = a Flutter widget build error in **release mode** (the red
  error screen becomes grey). Typical iPad-only causes: `Expanded`/`Flexible`
  in an unbounded parent, fixed heights that overflow, `!` on data that's null
  for a fresh account, `MediaQuery`-based math producing negative sizes, images
  that fail to load with no `errorBuilder`.
  Find it: `flutter run --release -d "iPad Air 11-inch (M3)"`, or debug mode on
  iPad and look for `RenderFlex`/`ParentDataWidget`/`Null check` errors; run
  with a **brand-new account** (empty profile, no data).
  Defend: set `ErrorWidget.builder` to a friendly fallback, add
  `FlutterError.onError` + Crashlytics/Sentry to see reviewer crashes.
- **Screenshots**: if `TARGETED_DEVICE_FAMILY` includes `2`, upload real iPad
  screenshots taken on an iPad 13" simulator — not stretched iPhone images or
  phone frames. Majority must show the app in use (not splash/login).
- **Orientations**: iPad multitasking requires all four orientations in
  `UISupportedInterfaceOrientations~ipad`, unless `UIRequiresFullScreen` = YES.
- **Not targeting iPad?** Set `TARGETED_DEVICE_FAMILY = 1`. Apple still tests
  the phone app on iPad in compatibility mode, so it must still work there.

### R20 — General release-mode robustness · 2.1(a) `[seen]`

> "The registration process could not be completed, sending the record answer
> prompted an unidentified error message."

- Every onboarding step must work on a **fresh install** on iPad with the
  latest iPadOS, on a slow network, with optional fields left empty, with
  permission requests **denied**.
- Never show raw/unknown errors; show a retry with a human message.
- Check that the backend used by the release build is production, reachable
  from outside your country (reviewers are mostly in the US), not IP-blocked,
  and not behind a VPN.

---

## Manual checklist (can't be checked from code)

Ask the user about each:

- [ ] Demo account (username + password) entered in **App Review Information**
      and **TestFlight → Beta App Review Information**; works today; no OTP/2FA;
      not subscribed (R22).
- [ ] Review Notes explain: login, where key features are, AI consent screen,
      unused frameworks, tracking status, why any required field is required.
- [ ] Screenshots: real device UI for each device family, no stretched iPhone
      images on iPad, majority show features not splash/login, match current UI
      (update after adding Sign in with Apple).
- [ ] App Store Connect Privacy Policy URL set and loads.
- [ ] App Description has Terms of Use (EULA) link, or custom EULA set (subscriptions).
- [ ] Paid Apps Agreement active (Business section), banking + tax complete (IAP).
- [ ] Every IAP/subscription "Ready to Submit", with review screenshot and
      review note, attached to this version (first submission) (R23).
- [ ] Promoted IAP images: unique art, no price, legible (R24).
- [ ] App Privacy answers match the code and the policy (see `privacy-policy.md`).
- [ ] Age rating questionnaire matches content (AI chat / user-generated
      content → answer accordingly; UGC needs report/block, `[common]` 1.2).
- [ ] Tested on iPad, latest iPadOS, release build, fresh install, and as an
      **update** over the previous App Store version.
