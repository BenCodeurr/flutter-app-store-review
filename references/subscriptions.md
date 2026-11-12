# Subscriptions & In-App Purchase checklist

Read this only if the app sells digital content, features or subscriptions.
In the source history, the subscription flow was rejected in **seven separate
review rounds** for different reasons (products not submitted, error in
sandbox, EULA link missing in metadata, paywall forcing Sign in with Apple,
promo codes, web payments, promo image with price). Walk every section.

## 1. Identify the stack

| Package | Notes |
|---|---|
| `in_app_purchase` (+ `in_app_purchase_storekit`) | Official. You own receipt validation and entitlement logic. |
| `purchases_flutter` / `purchases_ui_flutter` (RevenueCat) | Needs App Store Connect **In-App Purchase Key** (or shared secret) in RevenueCat; Offerings must be configured. |
| `adapty_flutter`, `qonversion_flutter`, `superwallkit_flutter`, `flutter_inapp_purchase`, `apphud` | Same principles; check their dashboard product IDs. |

## 2. Why the purchase fails in review (2.1(b) "an error message appeared")

Apple reviews IAP in the **sandbox**, with a **production-signed** build, and
products that are **not yet approved**. Products work in review without prior
approval — *if* everything below is right. Check in this order:

### App Store Connect / business
1. **Paid Apps Agreement** is active (Business → Agreements), banking and tax
   forms complete. If it's pending or expired, StoreKit returns no products →
   your app shows an error. Agreements must be accepted by the **Account
   Holder**; renewed agreements must be re-accepted.
2. Every product is **Ready to Submit** (not "Missing Metadata"): reference
   name, product ID, price, at least one localization (display name +
   description), **review screenshot** (a screenshot of the paywall), review
   notes. Subscriptions also need a subscription group with a localization.
3. **First submission of IAPs**: products must be attached to the app version
   (version page → "In-App Purchases and Subscriptions" → select them) and
   submitted **together with a new binary**. Later products can be submitted
   on their own.
4. If the app was rejected, products go to "Rejected" / "Developer Action
   Needed" too — re-select them when resubmitting.
5. Product availability: the products must be available in the reviewer's
   storefront (US) — check Pricing and Availability.

### Code
6. **Product IDs match exactly** (case-sensitive) between code / RevenueCat
   dashboard and App Store Connect.
7. **Handle missing products gracefully**: `queryProductDetails` returns
   `notFoundIDs`; RevenueCat `getOfferings()` may return `current == null`.
   Show "Subscriptions are temporarily unavailable, please try again" with a
   retry — never a crash, empty screen or "Error: null". (Scanner R12.)
8. **Don't hardcode prices**; use `ProductDetails.price` / `StoreProduct.priceString`.
9. **Complete transactions**: with `in_app_purchase`, call
   `completePurchase()` when `pendingCompletePurchase` is true, otherwise the
   next purchase attempt fails / hangs. Listen to `purchaseStream` from app
   start, not only on the paywall.
10. Handle `PurchaseStatus.canceled`, `pending` (Ask to Buy), `error`
    distinctly. Cancel is not an error — don't show an error dialog for it.
11. **Restore Purchases** button that calls `restorePurchases()` /
    `Purchases.restorePurchases()` and shows the result.

### Backend validation (the most common hidden cause)
12. Receipts from review are **sandbox** receipts even in a production build.
    - Legacy `verifyReceipt`: call production first; if status is **21007**,
      retry against `https://sandbox.itunes.apple.com/verifyReceipt`.
    - App Store Server API / JWS (`signedTransactionInfo`): accept
      `environment == "Sandbox"` (verify with the sandbox endpoint/root certs),
      don't reject it.
    - Shared secret / In-App Purchase key configured for this app.
13. The backend must not reject the purchase because the Apple ID's email
    differs from the account email (reviewers use their own sandbox Apple ID).
14. App Store Server Notifications URL set (sandbox **and** production) if your
    entitlement logic depends on them.
15. If the backend grants entitlement asynchronously, the app must poll/refresh
    and not show an error while waiting.

### Login and the paywall (seen twice)
16. If the user is logged in (demo account), the purchase must **not** trigger
    Sign in with Apple or any re-authentication. Check the paywall route guards,
    "link account" calls and token refresh logic.
17. If purchases require an account, explain it before showing the paywall and
    offer all login methods. Otherwise let guests purchase (anonymous app user
    ID) and restore/transfer on login.

### Test it the way Apple does
18. Create a **Sandbox tester** (Users and Access → Sandbox). On an **iPad
    simulator or device**, install a **TestFlight** build (closest to review)
    or a release build, log in with the demo account, buy, cancel, restore.
19. Also test with a StoreKit Configuration file in Xcode for fast iteration —
    but that doesn't test the App Store Connect setup or the backend; sandbox
    does.
20. Test with a demo account that **had** a subscription that **expired**
    (Apple asked for exactly this). In sandbox, subscriptions renew fast
    (1 month = 5 minutes) and stop after a few renewals — use that to produce an
    expired state.

## 3. Paywall content (3.1.2(c), seen ×3)

On the purchase screen, visible before buying:
- [ ] Subscription name (e.g. "Premium Monthly")
- [ ] Duration ("1 month", "1 year")
- [ ] Price from StoreKit, and per-unit price if you show savings
- [ ] Free trial terms: length and what's charged afterwards
- [ ] "Payment will be charged to your Apple ID account at confirmation of
      purchase. Subscription automatically renews unless cancelled at least 24
      hours before the end of the current period. Manage in Account Settings."
      (not strictly required, but reviewers like it)
- [ ] Tappable **Terms of Use (EULA)** link
- [ ] Tappable **Privacy Policy** link
- [ ] **Restore Purchases**
- [ ] The price/charge is the most prominent pricing element (don't make
      "€0.99/week" huge and "billed €51.48 yearly" tiny) `[common 3.1.2]`
- [ ] Close button clearly visible `[common]`

In App Store Connect:
- [ ] Privacy Policy URL
- [ ] EULA: standard → add `Terms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`
      to the **App Description**; custom → App Information → License Agreement.
      *(This one alone caused two rejections and one automated rejection.)*

## 4. Things that must not exist on iOS (3.1.1)

- Web checkout / Stripe / PayPal / Paystack / Flutterwave / Razorpay for
  digital content, inside a WebView or via a native SDK.
- Custom promo / coupon / referral / activation codes that unlock paid features
  → replace with App Store **offer codes** (`presentCodeRedemptionSheet`).
- Text like "cheaper on our website" (outside the US storefront exception).
- "Contact us to upgrade" flows.

Gate with `if (Platform.isIOS)`; consider a build flavor so the web payment
code isn't even in the iOS binary (also avoids R14 PassKit questions).

## 5. Promoted IAPs & win-back offers (2.3.2, seen)

- Promotional image 1024×1024: original artwork, no screenshot of the app, no
  price, no small text.
- Display name ≤ 30 chars, description ≤ 45 chars, no price, no "50% off".
- Not promoting? Delete the promotional image.

## 6. Review Notes for a subscription app

Use the template in `asc-templates.md` → "Subscription app".
