# App Store Connect text templates

Fill in `<…>` with real details. Only include paragraphs that apply to the
detected app profile. Keep it short and factual — reviewers skim.

## Review Notes (App Review Information → Notes)

```
DEMO ACCOUNT
Username: <email>   Password: <entered in the Sign-in fields>
This account has no active subscription, so the full purchase flow can be tested.
<If OTP login:> Phone login: use <number> and code <123456> (fixed code for review only).

HOW TO USE THE APP
1. Log in with the demo account (or tap "Continue as guest").
2. <Main feature> is on the <tab> tab: <one sentence>.
3. <Second feature>: <where>.

SUBSCRIPTIONS
Subscriptions are offered on the <screen> screen (<how to reach it>).
Products: <product names>. Terms of Use and Privacy Policy links are shown on that
screen, and Restore Purchases is at the bottom. The Terms of Use link is also in the
App Description.

THIRD-PARTY AI
When the user first opens <AI feature>, the app shows a consent screen explaining
that <data> is sent to <provider> for <purpose>. Nothing is sent before the user taps
"Allow". Consent can be withdrawn in Settings → Privacy.
<or:> The app does not send any user data to a third-party AI service.

FRAMEWORKS
The app does not use Apple Pay or Tap to Pay. PassKit / ProximityReader are linked
by <SDK>, used for <purpose / not used on iOS>.
<Tracking:> The app does not track users; App Privacy declares no tracking and the
app does not request ATT permission.
<or:> The ATT prompt appears on first launch after the welcome screen, before any
tracking SDK is initialized. Screen recording: <link>.

PROFILE FIELDS
Only <name and email> are required. <Country, city, occupation, phone> are optional.
<If something must be required:> <Field> is required because <legal/core reason>.

ACCOUNT DELETION
Settings → Account → Delete account.
```

## Reply to reviewer (Resolution Center)

Reply point by point, using the guideline numbers from the rejection:

```
Hello,

Thank you for the review. We have addressed every issue in build <version (build)>:

Guideline 5.1.1(v): <Fields> are now optional on the sign-up and profile screens.
Users can continue without filling them.

Guideline 3.1.2(c): The paywall now shows the subscription title, length, price,
and functional links to the Terms of Use and Privacy Policy. The App Description now
includes the Terms of Use link: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/

Guideline 2.1(b): All subscriptions are now submitted with this version, and the
Paid Apps Agreement is active. We tested the purchase flow in the sandbox on an
iPad Air (iPadOS <version>) with the demo account.

Guideline 2.1 (ATT): <…>

A screen recording showing these changes is attached / available at <link>.

Best regards,
<name>
```

## Reply when the reviewer is wrong / feature exists

```
Hello,

Thank you for your feedback. Regarding Guideline <x>: <feature> is available in the
app. To find it: <steps>. We attached a screen recording from a fresh install on
<device>. We also added these steps to the Review Notes for future submissions.
```

## App Description footer (subscription apps)

```
Subscription details:
• <Name>: <length>, <price> (prices may vary by region)
• Payment is charged to your Apple ID at confirmation of purchase.
• The subscription renews automatically unless cancelled at least 24 hours before
  the end of the current period. Manage or cancel in your App Store account settings.

Privacy Policy: <url>
Terms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

## TestFlight → Beta App Review Information

Same demo credentials as above. TestFlight review is separate from App Store
review: fill it in **separately**, including "Sign-in required" and Notes.
