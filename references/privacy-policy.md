# Privacy policy comparison & App Privacy answers

Goal: the privacy policy, the in-app disclosures, the App Store Connect "App
Privacy" answers and the actual code must all say the same thing. Apple checks
policy content against guideline 5.1.1(i) and 5.1.2(i), and rejected the
source app because a third-party AI service wasn't disclosed in the app.

## 1. Get the policy

1. Ask for the privacy policy URL (and Terms of Use URL) if not provided.
2. Fetch it with WebFetch. If the page is empty (JS-rendered), blocked, or a
   PDF you can't read, ask the user to paste the text.
3. Also check that the URL loads over HTTPS without login, and that it is the
   same URL as in App Store Connect and inside the app (scanner R21 lists URLs
   found in `lib/`).

## 2. Build the data inventory

From the scanner JSON:

- `data_inventory` — data types implied by packages, permissions and form
  fields, each with its source (`package:firebase_analytics`,
  `form:phone`, `permission:NSMicrophoneUsageDescription`).
- `third_parties` — SDK vendors (Google/Firebase, Meta, RevenueCat, Sentry,
  OneSignal, Mixpanel, AppsFlyer, OpenAI…).
- `ai_services` — AI providers seen in code.

Then add what the user told you about the backend (AI providers on the server,
email providers, hosting region, analytics on the server, data retention,
whether data is sold/shared for ads).

Map each item to Apple's App Privacy categories:

| Apple category | Typical Flutter sources |
|---|---|
| Contact Info → Name, Email, Phone, Physical Address | sign-up forms, `sign_in_with_apple`, `google_sign_in`, `firebase_auth` |
| Health & Fitness | `health`, HealthKit |
| Financial Info | payment forms (not IAP — Apple handles that) |
| Location → Precise / Coarse | `geolocator`, `location`, IP-based geo on server; city/country fields = Coarse |
| Sensitive Info | ethnicity, religion, sexual orientation, biometrics, etc. |
| Contacts | `flutter_contacts`, `contacts_service` |
| User Content → Photos/Videos, Audio, Customer Support, Other | `image_picker`, `camera`, `record`, `flutter_sound`, chat, uploads |
| Browsing / Search History | in-app search logs |
| Identifiers → User ID, Device ID | your account ID, `firebase_messaging` token, IDFA (`app_tracking_transparency`), `device_info_plus`, analytics instance IDs |
| Purchases | `in_app_purchase`, RevenueCat (purchase history) |
| Usage Data → Product Interaction, Advertising Data | `firebase_analytics`, `mixpanel_flutter`, `amplitude_flutter`, `posthog_flutter`, ads SDKs |
| Diagnostics → Crash Data, Performance | `firebase_crashlytics`, `sentry_flutter`, `firebase_performance` |
| Other Data | occupation, job, education, etc. |

For each type decide: **Linked to user?** (yes if tied to the account),
**Used for tracking?** (only if combined with third-party data for ads or
shared with brokers), **Purposes** (App Functionality, Analytics, Product
Personalization, Developer's Advertising, Third-Party Advertising, Other).

## 3. Gap table

Produce a table like:

| Data / party | Source in app | In policy? | Where / what's missing |
|---|---|---|---|
| Audio recordings | `record` package, mic permission | ❌ | Not mentioned |
| OpenAI (AI scoring) | backend (user confirmed) | ❌ | Must name provider, data sent, purpose, retention, training |
| Phone number | sign-up form (optional) | ✅ | §2 |
| Firebase Crashlytics | `firebase_crashlytics` | ⚠️ | Says "analytics tools", should name Google/Firebase and crash data |

Also check the policy has:
- [ ] Who the controller is + contact email/address
- [ ] What is collected, **how** (directly, automatically, from third parties)
- [ ] **All uses** of each data type
- [ ] **Every third party** that receives data, by name or clear category, and
      that they provide equal protection (5.1.1(i) wording)
- [ ] **Third-party AI services**: name, data sent, purpose, whether used for
      training, retention
- [ ] Retention period / deletion policy
- [ ] How to **delete the account and data** (in-app path + email)
- [ ] How to withdraw consent (AI, tracking, marketing)
- [ ] Tracking / advertising statement consistent with ATT and App Privacy
- [ ] Children: if the app may be used by under-13s (or under-16 EU), say so
      and describe parental consent — or state the app isn't for children
- [ ] Payments: subscriptions processed by Apple; you don't receive card data
- [ ] International transfers (GDPR) if users in EU/UK
- [ ] Last-updated date

## 4. Proposed sections

For each ❌/⚠️, write a ready-to-paste section in the policy's language and
tone. Use `[CONFIRM: …]` for facts you don't know. Example for AI:

> **AI-powered features.** When you use [feature, e.g. "answer feedback"], we
> send [the audio recording of your answer and the question text] to
> [OpenAI, L.L.C.] to [transcribe and evaluate your answer]. We only send this
> data after you allow it in the app, and you can withdraw consent at any time
> in Settings → Privacy. [OpenAI] processes the data on our behalf under a data
> processing agreement and [does not use it to train its models / CONFIRM]. The
> data is retained by [OpenAI] for up to [30 days / CONFIRM] and by us for
> [CONFIRM]. [OpenAI] provides the same or equal protection of your data as
> stated in this policy.

Example for optional profile fields:

> **Profile information (optional).** You may choose to provide your country,
> city and occupation to personalize your experience. These fields are optional
> and you can remove them at any time in your profile.

## 5. App Privacy (nutrition label) draft

Output a table the user can follow in App Store Connect → App Privacy:

| Data type | Collected | Linked to user | Tracking | Purposes |
|---|---|---|---|---|
| Email Address | Yes | Yes | No | App Functionality |
| Audio Data | Yes | Yes | No | App Functionality |
| Crash Data | Yes | No | No | Analytics |

Rules:
- If any row says Tracking = Yes, the app **must** show the ATT prompt (R15).
- If no row says Tracking = Yes, remove ATT and `NSUserTrackingUsageDescription`.
- Data processed only on-device and never sent off-device is not "collected".
- Data sent to a third-party AI service **is** collected.
