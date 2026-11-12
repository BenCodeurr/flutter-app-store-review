#!/usr/bin/env python3
"""
Flutter App Store review pre-flight scanner.

Usage:
    python3 scan.py <flutter_project_root> [--app path/to/App.ipa|Runner.app] [--json out.json]

Stdlib only. Heuristic: findings marked REVIEW need a human/agent to confirm.
Rule IDs match references/rules.md.
"""
import argparse
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SEVERITY_ORDER = ["BLOCKER", "HIGH", "MEDIUM", "REVIEW", "INFO"]

# ---------------------------------------------------------------------------
# Knowledge tables
# ---------------------------------------------------------------------------

SOCIAL_LOGIN_PKGS = {
    "google_sign_in": "Google",
    "flutter_facebook_auth": "Facebook",
    "facebook_auth": "Facebook",
    "twitter_login": "Twitter/X",
    "flutter_line_sdk": "LINE",
    "flutter_naver_login": "Naver",
    "kakao_flutter_sdk": "Kakao",
    "kakao_flutter_sdk_user": "Kakao",
    "firebase_ui_oauth_google": "Google",
    "firebase_ui_oauth_facebook": "Facebook",
    "flutter_web_auth": "OAuth (web)",
    "flutter_web_auth_2": "OAuth (web)",
    "flutter_appauth": "OAuth (AppAuth)",
    "msal_flutter": "Microsoft",
    "aad_oauth": "Microsoft",
}
APPLE_LOGIN_PKGS = {"sign_in_with_apple", "the_apple_sign_in", "apple_sign_in", "firebase_ui_oauth_apple"}
AUTH_PKGS = {"firebase_auth", "supabase_flutter", "amplify_auth_cognito", "appwrite", "auth0_flutter",
             "pocketbase", "parse_server_sdk_flutter"} | set(SOCIAL_LOGIN_PKGS) | APPLE_LOGIN_PKGS

IAP_PKGS = {
    "in_app_purchase": "in_app_purchase (official)",
    "in_app_purchase_storekit": "in_app_purchase (official)",
    "purchases_flutter": "RevenueCat",
    "purchases_ui_flutter": "RevenueCat Paywalls",
    "adapty_flutter": "Adapty",
    "qonversion_flutter": "Qonversion",
    "superwallkit_flutter": "Superwall",
    "flutter_inapp_purchase": "flutter_inapp_purchase",
    "apphud": "Apphud",
    "glassfy_flutter": "Glassfy",
}
EXTERNAL_PAYMENT_PKGS = {
    "flutter_stripe": "Stripe", "stripe_sdk": "Stripe", "stripe_payment": "Stripe",
    "flutter_paystack": "Paystack", "flutter_paystack_plus": "Paystack", "pay_with_paystack": "Paystack",
    "flutterwave_standard": "Flutterwave", "flutterwave": "Flutterwave",
    "razorpay_flutter": "Razorpay", "flutter_paypal": "PayPal", "flutter_paypal_payment": "PayPal",
    "flutter_braintree": "Braintree", "square_in_app_payments": "Square", "pay": "Apple/Google Pay (pay)",
    "mek_stripe_terminal": "Stripe Terminal", "flutter_stripe_terminal": "Stripe Terminal",
    "mollie_flutter": "Mollie", "cashfree_pg": "Cashfree",
}
WEBVIEW_PKGS = {"webview_flutter", "flutter_inappwebview", "flutter_webview_plugin", "url_launcher"}

AI_PKGS = {
    "google_generative_ai": "Google Gemini", "firebase_ai": "Google Gemini (Firebase AI)",
    "firebase_vertexai": "Google Vertex AI", "dart_openai": "OpenAI", "openai_dart": "OpenAI",
    "chat_gpt_sdk": "OpenAI", "langchain": "LangChain (LLM)", "langchain_openai": "OpenAI",
    "langchain_google": "Google Gemini", "anthropic_sdk_dart": "Anthropic", "mistralai_dart": "Mistral",
    "ollama_dart": "Ollama", "elevenlabs_flutter": "ElevenLabs", "deepgram_speech_to_text": "Deepgram",
    "flutter_gemini": "Google Gemini", "gpt_markdown": None,
}
AI_HOSTS = {
    "api.openai.com": "OpenAI", "generativelanguage.googleapis.com": "Google Gemini",
    "aiplatform.googleapis.com": "Google Vertex AI", "api.anthropic.com": "Anthropic",
    "api.mistral.ai": "Mistral", "api.groq.com": "Groq", "openrouter.ai": "OpenRouter",
    "api.elevenlabs.io": "ElevenLabs", "api.deepgram.com": "Deepgram", "api.assemblyai.com": "AssemblyAI",
    "api.together.xyz": "Together AI", "api.replicate.com": "Replicate", "api.cohere.ai": "Cohere",
    "api.cohere.com": "Cohere", "api.perplexity.ai": "Perplexity", "api.x.ai": "xAI",
    "openai.azure.com": "Azure OpenAI", "api.deepseek.com": "DeepSeek",
}

TRACKING_PKGS = {
    "app_tracking_transparency": "ATT plugin",
    "facebook_app_events": "Meta App Events", "flutter_facebook_app_events": "Meta App Events",
    "appsflyer_sdk": "AppsFlyer", "adjust_sdk": "Adjust", "branch_flutter_sdk": "Branch",
    "google_mobile_ads": "Google AdMob", "applovin_max": "AppLovin", "unity_ads_plugin": "Unity Ads",
    "ironsource_mediation": "ironSource", "singular_flutter_sdk": "Singular", "kochava_tracker": "Kochava",
    "tiktok_events_sdk": "TikTok Events",
}

# plugin -> (required Info.plist keys, description)
PERMISSION_PLUGINS = {
    "image_picker": (["NSPhotoLibraryUsageDescription", "NSCameraUsageDescription"], "photo/camera picker"),
    "camera": (["NSCameraUsageDescription", "NSMicrophoneUsageDescription"], "camera (records audio with video)"),
    "mobile_scanner": (["NSCameraUsageDescription"], "QR/barcode scanner"),
    "qr_code_scanner": (["NSCameraUsageDescription"], "QR scanner"),
    "record": (["NSMicrophoneUsageDescription"], "audio recording"),
    "flutter_sound": (["NSMicrophoneUsageDescription"], "audio recording"),
    "audio_waveforms": (["NSMicrophoneUsageDescription"], "audio recording"),
    "speech_to_text": (["NSMicrophoneUsageDescription", "NSSpeechRecognitionUsageDescription"], "speech recognition"),
    "geolocator": (["NSLocationWhenInUseUsageDescription"], "location"),
    "location": (["NSLocationWhenInUseUsageDescription"], "location"),
    "google_maps_flutter": ([], "maps"),
    "flutter_contacts": (["NSContactsUsageDescription"], "contacts"),
    "contacts_service": (["NSContactsUsageDescription"], "contacts"),
    "local_auth": (["NSFaceIDUsageDescription"], "Face ID"),
    "app_tracking_transparency": (["NSUserTrackingUsageDescription"], "ATT"),
    "device_calendar": (["NSCalendarsUsageDescription"], "calendar"),
    "add_2_calendar": (["NSCalendarsUsageDescription"], "calendar"),
    "health": (["NSHealthShareUsageDescription"], "HealthKit"),
    "flutter_blue_plus": (["NSBluetoothAlwaysUsageDescription"], "Bluetooth"),
    "flutter_reactive_ble": (["NSBluetoothAlwaysUsageDescription"], "Bluetooth"),
    "photo_manager": (["NSPhotoLibraryUsageDescription"], "photo library"),
    "wechat_assets_picker": (["NSPhotoLibraryUsageDescription"], "photo library"),
    "image_gallery_saver": (["NSPhotoLibraryAddUsageDescription"], "save to photos"),
    "gal": (["NSPhotoLibraryAddUsageDescription"], "save to photos"),
    "agora_rtc_engine": (["NSCameraUsageDescription", "NSMicrophoneUsageDescription"], "video calls"),
    "flutter_webrtc": (["NSCameraUsageDescription", "NSMicrophoneUsageDescription"], "WebRTC calls"),
    "zego_express_engine": (["NSCameraUsageDescription", "NSMicrophoneUsageDescription"], "video calls"),
    "nfc_manager": (["NFCReaderUsageDescription"], "NFC"),
    "flutter_nfc_kit": (["NFCReaderUsageDescription"], "NFC"),
    "motion_sensors": (["NSMotionUsageDescription"], "motion"),
    "pedometer": (["NSMotionUsageDescription"], "motion/pedometer"),
    "file_picker": ([], "files"),
}
# key -> plugins that justify it (for "unused" check). permission_handler justifies anything.
KEY_TO_PLUGINS = {}
for _p, (_keys, _) in PERMISSION_PLUGINS.items():
    for _k in _keys:
        KEY_TO_PLUGINS.setdefault(_k, set()).add(_p)
KEY_TO_PLUGINS.setdefault("NSLocationAlwaysAndWhenInUseUsageDescription", set()).update({"geolocator", "location", "background_location"})
KEY_TO_PLUGINS.setdefault("NSLocationAlwaysUsageDescription", set()).update({"geolocator", "location"})
KEY_TO_PLUGINS.setdefault("NSPhotoLibraryAddUsageDescription", set()).update({"image_picker", "photo_manager"})
KEY_TO_PLUGINS.setdefault("NSMicrophoneUsageDescription", set()).update({"image_picker", "video_player"})
KEY_TO_PLUGINS.setdefault("NSCalendarsFullAccessUsageDescription", set()).update({"device_calendar", "add_2_calendar"})
KEY_TO_PLUGINS.setdefault("NSHealthUpdateUsageDescription", set()).add("health")
KEY_TO_PLUGINS.setdefault("NSBluetoothPeripheralUsageDescription", set()).update({"flutter_blue_plus", "flutter_reactive_ble"})

VAGUE_PATTERNS = [
    r"\bneeds? (access|permission)\b", r"\bwould like to access\b", r"\brequires? (access|permission)\b",
    r"\bfor (app )?functionality\b", r"\bto (work|function) (properly|correctly)\b", r"^\s*(allow|access)\b",
    r"\bwants? to (use|access)\b", r"\bpermission (is )?required\b", r"\$\(PRODUCT_NAME\) (needs|requires)",
    r"^\s*\$?\(?[A-Z_]*\)?\s*$",
]

# package -> (Apple App Privacy data types, third party)
SDK_DATA_MAP = {
    "firebase_analytics": (["Usage Data: Product Interaction", "Identifiers: Device ID"], "Google (Firebase Analytics)"),
    "firebase_crashlytics": (["Diagnostics: Crash Data"], "Google (Firebase Crashlytics)"),
    "firebase_performance": (["Diagnostics: Performance Data"], "Google (Firebase Performance)"),
    "firebase_messaging": (["Identifiers: Device ID (push token)"], "Google (Firebase Cloud Messaging)"),
    "firebase_auth": (["Contact Info: Email Address", "Identifiers: User ID"], "Google (Firebase Auth)"),
    "cloud_firestore": (["(stores whatever you write)"], "Google (Cloud Firestore)"),
    "firebase_storage": (["User Content (uploaded files)"], "Google (Firebase Storage)"),
    "google_sign_in": (["Contact Info: Name, Email Address", "Identifiers: User ID"], "Google (Sign-In)"),
    "sign_in_with_apple": (["Contact Info: Name, Email Address", "Identifiers: User ID"], "Apple (Sign in with Apple)"),
    "flutter_facebook_auth": (["Contact Info: Name, Email Address", "Identifiers: User ID"], "Meta (Facebook Login)"),
    "facebook_app_events": (["Usage Data", "Identifiers: Device ID", "Advertising Data"], "Meta (App Events)"),
    "sentry_flutter": (["Diagnostics: Crash Data, Performance Data"], "Sentry"),
    "onesignal_flutter": (["Identifiers: Device ID", "Usage Data"], "OneSignal"),
    "mixpanel_flutter": (["Usage Data: Product Interaction", "Identifiers"], "Mixpanel"),
    "amplitude_flutter": (["Usage Data: Product Interaction", "Identifiers"], "Amplitude"),
    "posthog_flutter": (["Usage Data: Product Interaction", "Identifiers"], "PostHog"),
    "appsflyer_sdk": (["Identifiers: Device ID", "Usage Data", "Advertising Data"], "AppsFlyer"),
    "adjust_sdk": (["Identifiers: Device ID", "Usage Data", "Advertising Data"], "Adjust"),
    "google_mobile_ads": (["Identifiers: Device ID", "Usage Data: Advertising Data", "Location: Coarse"], "Google (AdMob)"),
    "purchases_flutter": (["Purchases: Purchase History", "Identifiers: User ID"], "RevenueCat"),
    "adapty_flutter": (["Purchases: Purchase History", "Identifiers: User ID"], "Adapty"),
    "qonversion_flutter": (["Purchases: Purchase History", "Identifiers: User ID"], "Qonversion"),
    "in_app_purchase": (["Purchases: Purchase History"], None),
    "intercom_flutter": (["Contact Info", "User Content: Customer Support"], "Intercom"),
    "zendesk_messaging": (["Contact Info", "User Content: Customer Support"], "Zendesk"),
    "supabase_flutter": (["(stores whatever you write)", "Contact Info: Email Address"], "Supabase"),
    "google_maps_flutter": (["Location (if user location shown)"], "Google Maps"),
    "agora_rtc_engine": (["User Content: Audio/Video"], "Agora"),
    "stream_chat_flutter": (["User Content: Other User Content"], "Stream"),
    "flutter_branch_sdk": (["Identifiers: Device ID", "Usage Data"], "Branch"),
    "clarity_flutter": (["Usage Data: Product Interaction"], "Microsoft Clarity"),
    "smartlook": (["Usage Data: Product Interaction"], "Smartlook"),
    "datadog_flutter_plugin": (["Diagnostics"], "Datadog"),
    "bugsnag_flutter": (["Diagnostics: Crash Data"], "Bugsnag"),
}
PERMISSION_DATA = {
    "NSMicrophoneUsageDescription": "User Content: Audio Data",
    "NSCameraUsageDescription": "User Content: Photos or Videos",
    "NSPhotoLibraryUsageDescription": "User Content: Photos or Videos",
    "NSLocationWhenInUseUsageDescription": "Location: Precise or Coarse",
    "NSLocationAlwaysAndWhenInUseUsageDescription": "Location: Precise or Coarse",
    "NSContactsUsageDescription": "Contacts",
    "NSHealthShareUsageDescription": "Health & Fitness",
    "NSUserTrackingUsageDescription": "Identifiers: Device ID (IDFA) — tracking",
    "NSSpeechRecognitionUsageDescription": "User Content: Audio Data",
}

# form-field keyword -> (label, Apple category)
FIELD_KEYWORDS = {
    r"country|nationality|country of origin|pays": ("country/nationality", "Location: Coarse / Other Data"),
    r"\bcity\b|ville|town|region\b|state\b|province": ("city/region", "Location: Coarse"),
    r"occupation|\bjob\b|profession|employer|company|métier|work title|job title": ("occupation/job", "Other Data"),
    r"phone|mobile number|telephone|téléphone|msisdn": ("phone", "Contact Info: Phone Number"),
    r"gender|\bsex\b|genre": ("gender", "Other Data / Sensitive"),
    r"birth|\bdob\b|\bage\b|birthday|naissance": ("date of birth/age", "Other Data"),
    r"address|street|zip|postal|postcode|adresse": ("physical address", "Contact Info: Physical Address"),
    r"marital|religion|ethnic|income|salary|revenu": ("sensitive (marital/religion/income)", "Sensitive Info"),
    r"school|education|university|degree": ("education", "Other Data"),
}

PROMO_RE = re.compile(r"promo ?code|coupon|voucher|redeem ?code|referral ?code|activation ?code|gift ?code|access ?code|code promo", re.I)
PAY_URL_RE = re.compile(r"https?://[^\s'\"]*(checkout|payment|billing|pricing|subscribe|stripe|paystack|paypal|flutterwave|razorpay|gumroad|lemonsqueezy|buy)[^\s'\"]*", re.I)
URL_RE = re.compile(r"https?://[^\s'\"\)\}]+")

findings = []


def add(rule, severity, guideline, message, file=None, line=None, fix=None):
    findings.append({"rule": rule, "severity": severity, "guideline": guideline, "message": message,
                     "file": file, "line": line, "fix": fix})


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def parse_pubspec_deps(text):
    deps, section = {}, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw.startswith((" ", "\t")):
            section = line.strip().rstrip(":")
            continue
        if section in ("dependencies", "dev_dependencies", "dependency_overrides"):
            m = re.match(r"^  ([A-Za-z0-9_]+)\s*:", line)
            if m:
                deps[m.group(1)] = section
    return deps


def parse_lock_packages(text):
    pkgs, in_pkgs = set(), False
    for line in text.splitlines():
        if line.startswith("packages:"):
            in_pkgs = True
            continue
        if in_pkgs and line and not line.startswith(" "):
            break
        m = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if in_pkgs and m:
            pkgs.add(m.group(1))
    return pkgs


def parse_podfile_lock(text):
    pods, in_pods = set(), False
    for line in text.splitlines():
        if line.startswith("PODS:"):
            in_pods = True
            continue
        if in_pods and line and not line.startswith(" "):
            break
        m = re.match(r'^  - "?([A-Za-z0-9_\-+./]+)', line)
        if in_pods and m:
            pods.add(m.group(1).split("/")[0])
    return pods


def load_plist(p):
    try:
        with open(p, "rb") as f:
            return plistlib.load(f)
    except Exception as e:
        return {"__error__": str(e)}


def dart_files(root):
    lib = Path(root) / "lib"
    if not lib.exists():
        return []
    out = []
    for p in lib.rglob("*.dart"):
        n = p.name
        if n.endswith((".g.dart", ".freezed.dart", ".gr.dart", ".config.dart", ".mocks.dart")) or "l10n" in p.parts:
            continue
        out.append(p)
    return out


def rel(root, p):
    try:
        return str(Path(p).relative_to(root))
    except ValueError:
        return str(p)


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


# ---------------------------------------------------------------------------
# Binary inspection
# ---------------------------------------------------------------------------

def inspect_app(app_path):
    """Return set of linked system frameworks of interest, or None."""
    interesting = {"PassKit", "ProximityReader", "AppTrackingTransparency", "AdSupport", "StoreKit",
                   "AuthenticationServices", "HealthKit", "CoreLocation", "Contacts", "AVFoundation"}
    if not shutil.which("otool"):
        return None, "otool not available (needs macOS with Xcode command line tools)"
    tmp = None
    p = Path(app_path)
    if p.suffix == ".ipa":
        tmp = tempfile.mkdtemp(prefix="ipa_")
        with zipfile.ZipFile(p) as z:
            z.extractall(tmp)
        apps = list(Path(tmp, "Payload").glob("*.app"))
        if not apps:
            return None, "no .app in ipa"
        p = apps[0]
    binaries = []
    info = load_plist(p / "Info.plist")
    exe = info.get("CFBundleExecutable") if isinstance(info, dict) else None
    if exe and (p / exe).exists():
        binaries.append(p / exe)
    fw = p / "Frameworks"
    if fw.exists():
        for f in fw.glob("*.framework"):
            b = f / f.stem
            if b.exists():
                binaries.append(b)
    linked = {}
    for b in binaries:
        try:
            out = subprocess.run(["otool", "-L", str(b)], capture_output=True, text=True, timeout=60).stdout
        except Exception:
            continue
        for name in interesting:
            if f"/{name}.framework/" in out:
                linked.setdefault(name, set()).add(b.name)
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return {k: sorted(v) for k, v in linked.items()}, None


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def scan(root, app=None):
    root = Path(root).resolve()
    pubspec = read(root / "pubspec.yaml")
    if not pubspec:
        print(f"error: no pubspec.yaml in {root}", file=sys.stderr)
        sys.exit(2)
    direct = parse_pubspec_deps(pubspec)
    lock_pkgs = parse_lock_packages(read(root / "pubspec.lock"))
    all_pkgs = set(direct) | lock_pkgs
    pods = parse_podfile_lock(read(root / "ios" / "Podfile.lock"))

    info_path = root / "ios" / "Runner" / "Info.plist"
    info = load_plist(info_path) if info_path.exists() else {}
    if "__error__" in info:
        add("R00", "INFO", "-", f"Could not parse Info.plist: {info['__error__']}", rel(root, info_path))
        info = {}

    entitlements = {}
    for e in (root / "ios" / "Runner").glob("*.entitlements"):
        d = load_plist(e)
        if "__error__" not in d:
            entitlements[rel(root, e)] = d
    pbx = read(root / "ios" / "Runner.xcodeproj" / "project.pbxproj")

    files = dart_files(root)
    sources = {f: read(f) for f in files}
    all_src = "\n".join(sources.values())

    def grep(pattern, flags=re.I):
        rx = re.compile(pattern, flags)
        for f, t in sources.items():
            for m in rx.finditer(t):
                yield f, line_of(t, m.start()), m

    def first(pattern, flags=re.I):
        for hit in grep(pattern, flags):
            return hit
        return None

    has = lambda pkg: pkg in direct  # direct deps for intent

    # ---------------- Profile ----------------
    iap_stack = sorted({v for k, v in IAP_PKGS.items() if has(k)})
    social = sorted({v for k, v in SOCIAL_LOGIN_PKGS.items() if has(k)})
    apple_login = any(has(p) for p in APPLE_LOGIN_PKGS) or bool(first(r"AppleAuthProvider|OAuthProvider\(\s*['\"]apple\.com"))
    if bool(first(r"GoogleAuthProvider")) and "Google" not in social:
        social.append("Google (Firebase provider)")
    if bool(first(r"FacebookAuthProvider")) and "Facebook" not in social:
        social.append("Facebook (Firebase provider)")
    supabase_oauth = first(r"signInWithOAuth\(\s*(OAuthProvider|Provider)\.(google|facebook|github|twitter|discord|azure)")
    if supabase_oauth:
        social.append(f"Supabase OAuth ({supabase_oauth[2].group(2)})")
    has_auth = any(has(p) for p in AUTH_PKGS) or bool(first(r"sign ?up|create account|register"))
    subs_in_code = bool(first(r"subscription|subscribe|premium|paywall|ProductDetails|Offerings|StoreProduct"))
    ai_services = {}
    for k, v in AI_PKGS.items():
        if v and has(k):
            ai_services.setdefault(v, []).append(f"package:{k}")
    for host, name in AI_HOSTS.items():
        hit = first(re.escape(host))
        if hit:
            ai_services.setdefault(name, []).append(f"{rel(root, hit[0])}:{hit[1]}")
    tracking = sorted({v for k, v in TRACKING_PKGS.items() if has(k)})
    family = sorted(set(re.findall(r"TARGETED_DEVICE_FAMILY = \"?([0-9,]+)\"?;", pbx)))
    ipad = any("2" in f.split(",") for f in family) if family else None
    ext_pay = sorted({v for k, v in EXTERNAL_PAYMENT_PKGS.items() if has(k)})

    profile = {
        "subscriptions_or_iap": bool(iap_stack),
        "iap_stack": iap_stack,
        "mentions_subscription_without_iap_package": (not iap_stack) and subs_in_code,
        "has_accounts": has_auth,
        "social_login": social,
        "sign_in_with_apple": apple_login,
        "external_payment_sdks": ext_pay,
        "ai_services_in_app": sorted(ai_services),
        "tracking_sdks": tracking,
        "ipad_supported": ipad,
        "targeted_device_family": family,
        "privacy_manifest": (root / "ios" / "Runner" / "PrivacyInfo.xcprivacy").exists(),
        "dart_files_scanned": len(files),
    }

    # ---------------- R01-R04 login ----------------
    if social and not apple_login:
        add("R01", "BLOCKER", "4.8", f"Third-party login ({', '.join(social)}) without Sign in with Apple.",
            "pubspec.yaml", fix="Add sign_in_with_apple; see rules.md R01.")
    if apple_login:
        ok = any(d.get("com.apple.developer.applesignin") for d in entitlements.values())
        if not ok:
            add("R02", "BLOCKER", "2.1(a)", "Sign in with Apple used but no com.apple.developer.applesignin entitlement in ios/Runner/*.entitlements.",
                fix="Xcode → Runner → Signing & Capabilities → + Sign in with Apple (Release config too).")
        elif entitlements and "CODE_SIGN_ENTITLEMENTS" not in pbx:
            add("R02", "HIGH", "2.1(a)", "Entitlements file exists but CODE_SIGN_ENTITLEMENTS not found in project.pbxproj.",
                "ios/Runner.xcodeproj/project.pbxproj")
        if has("sign_in_with_apple") and not first(r"SignInWithAppleButton"):
            hit = first(r"getAppleIDCredential")
            add("R03", "REVIEW", "4 (Design)", "Sign in with Apple uses a custom button. Confirm it matches the HIG (logo, border, same size as other login buttons).",
                rel(root, hit[0]) if hit else None, hit[1] if hit else None, "Use SignInWithAppleButton; rules.md R03.")
        if first(r"getAppleIDCredential") and not first(r"userIdentifier"):
            hit = first(r"getAppleIDCredential")
            add("R02", "REVIEW", "2.1(a)", "Apple credential is read but userIdentifier is never used. Apple only returns email/name on first sign-in; key accounts by userIdentifier and treat email as optional.",
                rel(root, hit[0]), hit[1])
        hit = first(r"credential\.email\s*!|\.email!")
        if hit:
            add("R02", "HIGH", "2.1(a)", "Force-unwrapping email. Apple sends email only on the first authorization, so this crashes for returning users (and reviewers).",
                rel(root, hit[0]), hit[1])
    if has("google_sign_in"):
        schemes = []
        for t in info.get("CFBundleURLTypes", []) or []:
            schemes += t.get("CFBundleURLSchemes", []) or []
        if not any(str(s).startswith("com.googleusercontent.apps.") for s in schemes):
            add("R04", "HIGH", "2.1(a)", "google_sign_in present but Info.plist has no com.googleusercontent.apps.* URL scheme (REVERSED_CLIENT_ID). Google login will fail.",
                "ios/Runner/Info.plist")
    if has_auth and not first(r"delete (my |your )?account|account deletion|deleteAccount|delete_account|supprimer (mon |le )?compte|eliminar cuenta"):
        add("R19", "HIGH", "5.1.1(v)", "App has accounts but no in-app account deletion found.", fix="Add Settings → Delete account; rules.md R19.")
    if first(r"verifyPhoneNumber|signInWithOtp|sendOtp|verifyOtp|OTP|one[- ]time (pass)?code"):
        hit = first(r"verifyPhoneNumber|signInWithOtp|sendOtp|verifyOtp")
        add("R22", "REVIEW", "2.1", "OTP/phone login detected. Reviewers can't receive codes: provide a demo account with password, or a fixed OTP for a whitelisted demo number.",
            rel(root, hit[0]) if hit else None, hit[1] if hit else None)

    # ---------------- R05 required fields ----------------
    form_fields = []
    for f, t in sources.items():
        lines = t.splitlines()
        for i, ln in enumerate(lines):
            low = ln.lower()
            if not re.search(r"labeltext|hinttext|label:|hint:|title:|text\(|placeholder|fieldname|name:", low):
                continue
            for rx, (label, cat) in FIELD_KEYWORDS.items():
                if not re.search(rx, low):
                    continue
                window = "\n".join(lines[max(0, i - 25): i + 25])
                if not re.search(r"TextFormField|TextField|DropdownButtonFormField|FormBuilder|CountryCodePicker|CountryPicker|IntlPhoneField|showCountryPicker|DropdownButton|InputDecoration", window):
                    continue
                optional = "optional" in low or "(optionnel" in low
                required = bool(re.search(r"validator\s*:", window)) and bool(
                    re.search(r"isEmpty|==\s*null|isBlank|required|trim\(\)\.length|\.length\s*<", window))
                form_fields.append({"field": label, "category": cat, "file": rel(root, f), "line": i + 1,
                                    "looks_required": required and not optional})
                if required and not optional:
                    add("R05", "REVIEW", "5.1.1(v)", f"'{label}' field looks REQUIRED (validator rejects empty). Apple rejects required personal info not essential to the app.",
                        rel(root, f), i + 1, "Make optional (no empty validation, '(optional)' label, backend accepts null).")
                break
    # dedupe R05 per file+label
    seen = set()
    for fnd in list(findings):
        if fnd["rule"] == "R05":
            key = (fnd["file"], fnd["message"])
            if key in seen:
                findings.remove(fnd)
            seen.add(key)

    # ---------------- R06-R08 purpose strings ----------------
    usage_keys = {k: v for k, v in info.items() if isinstance(k, str) and k.endswith("UsageDescription")}
    permissions = {}
    for k, v in usage_keys.items():
        permissions[k] = v
        s = str(v).strip()
        vague = len(s) < 40 or any(re.search(p, s, re.I) for p in VAGUE_PATTERNS)
        no_example = not re.search(r"for example|e\.g\.|such as|for instance|par exemple|por ejemplo|when you", s, re.I)
        if vague:
            add("R07", "HIGH", "5.1.1(ii)", f"{k} is vague: \"{s}\". Explain purpose + give a concrete example.", "ios/Runner/Info.plist")
        elif no_example:
            add("R07", "MEDIUM", "5.1.1(ii)", f"{k} has no concrete example: \"{s}\". Apple asked for 'a specific example of how the data will be used'.", "ios/Runner/Info.plist")
    for pkg, (keys, desc) in PERMISSION_PLUGINS.items():
        if pkg in direct:
            for k in keys:
                if k not in usage_keys:
                    sev = "HIGH" if not (pkg == "image_picker" and k == "NSCameraUsageDescription") else "MEDIUM"
                    add("R06", sev, "5.1.1(ii) / 2.1", f"{pkg} ({desc}) needs {k} in Info.plist — missing (crash when requested).", "ios/Runner/Info.plist")
    if "permission_handler" not in direct:
        for k in usage_keys:
            justifying = KEY_TO_PLUGINS.get(k, set())
            if justifying and not (justifying & all_pkgs):
                sev = "HIGH" if k == "NSUserTrackingUsageDescription" else "MEDIUM"
                add("R08", sev, "2.1 / 5.1.1", f"{k} declared but no plugin using it was found. Reviewers will look for this feature; remove it if unused.", "ios/Runner/Info.plist")

    # ---------------- R09-R13 payments ----------------
    if ext_pay:
        add("R09", "HIGH", "3.1.1", f"External payment SDKs: {', '.join(ext_pay)}. Allowed only for physical goods/services. Digital content/subscriptions must use IAP on iOS.",
            "pubspec.yaml", fix="Gate with Platform.isIOS or remove from iOS build; rules.md R09.")
    for f, ln, m in grep(PAY_URL_RE.pattern):
        add("R09", "REVIEW", "3.1.1", f"Payment-looking URL opened from the app: {m.group(0)[:100]}", rel(root, f), ln,
            "If this sells digital content, don't show it on iOS.")
    for f, ln, m in grep(PROMO_RE.pattern):
        add("R10", "HIGH" if profile["subscriptions_or_iap"] else "REVIEW", "3.1.1",
            f"Custom code redemption ('{m.group(0)}'). Codes that unlock paid features must be App Store offer codes.",
            rel(root, f), ln, "Use presentCodeRedemptionSheet(); rules.md R10.")
    # dedupe R10 to first 5
    r10 = [x for x in findings if x["rule"] == "R10"]
    for x in r10[5:]:
        findings.remove(x)

    if profile["subscriptions_or_iap"] or profile["mentions_subscription_without_iap_package"]:
        paywall_files = [f for f, t in sources.items() if re.search(
            r"buyNonConsumable|buyConsumable|purchasePackage|purchaseStoreProduct|makePurchase|Adapty\(\)\.makePurchase|purchaseProduct|RevenueCatUI|PaywallView|presentPaywall|queryProductDetails|getOfferings", t)]
        if not paywall_files and profile["subscriptions_or_iap"]:
            add("R11", "REVIEW", "3.1.2(c)", "IAP package present but no purchase call found in lib/. Check where purchases happen.")
        uses_rc_ui = any(re.search(r"RevenueCatUI|PaywallView|presentPaywall", sources[f]) for f in paywall_files)
        if paywall_files and not uses_rc_ui:
            # look in paywall files + files they live next to
            neighborhood = set(paywall_files)
            for f in paywall_files:
                neighborhood |= {g for g in sources if g.parent == f.parent}
            blob = "\n".join(sources[g] for g in neighborhood)
            pf = rel(root, paywall_files[0])
            checks = {
                "Terms of Use / EULA link": r"terms|eula|stdeula|conditions d'utilisation|cgu",
                "Privacy Policy link": r"privacy|confidentialit|privacidad",
                "price from StoreKit": r"\.price\b|priceString|localizedPrice|\.price\)|price:",
                "subscription period": r"month|year|week|annual|period|duration|subscriptionPeriod|mois|an\b",
            }
            for label, rx in checks.items():
                if not re.search(rx, blob, re.I):
                    add("R11", "HIGH", "3.1.2(c)", f"Paywall seems to lack: {label}.", pf,
                        fix="Required on the purchase screen; subscriptions.md §3.")
            hard_price = re.search(r"['\"][^'\"\n]{0,12}[\$€£₦]\s?\d+[.,]?\d*[^'\"\n]{0,20}['\"]|['\"][^'\"\n]{0,20}\d+[.,]\d{2}\s?(USD|EUR|GBP|NGN|FCFA|XOF|CAD|AUD)\b", blob)
            if hard_price:
                add("R11", "MEDIUM", "3.1.2 / 2.1(b)", f"Hardcoded price string {hard_price.group(0)[:40]} near paywall. Use StoreKit's localized price.", pf)
        if has("in_app_purchase") or has("in_app_purchase_storekit"):
            if first(r"queryProductDetails") and not first(r"notFoundIDs|productDetails\.isEmpty|\.productDetails\.isEmpty"):
                hit = first(r"queryProductDetails")
                add("R12", "HIGH", "2.1(b)", "queryProductDetails result: notFoundIDs / empty products not handled. In review this shows an error or blank paywall when products aren't available yet.",
                    rel(root, hit[0]), hit[1])
            if first(r"purchaseStream") and not first(r"completePurchase"):
                hit = first(r"purchaseStream")
                add("R12", "HIGH", "2.1(b)", "purchaseStream used but completePurchase() never called. Unfinished transactions break later purchases.",
                    rel(root, hit[0]), hit[1])
            if not first(r"PurchaseStatus\.canceled"):
                add("R12", "REVIEW", "2.1(b)", "PurchaseStatus.canceled not handled separately — don't show an error when the user cancels.")
        if has("purchases_flutter"):
            hit = first(r"getOfferings")
            if hit and not first(r"current\s*==\s*null|current\s*!=\s*null|\.current\?|current\s*\?\?"):
                add("R12", "HIGH", "2.1(b)", "RevenueCat getOfferings(): offerings.current null case not handled.", rel(root, hit[0]), hit[1])
            if first(r"PurchasesErrorCode") is None and first(r"purchasePackage|purchaseStoreProduct"):
                add("R12", "REVIEW", "2.1(b)", "RevenueCat purchase errors not inspected (PurchasesErrorCode.purchaseCancelledError should not show an error).")
        if not first(r"restorePurchases|restoreTransactions|restore_purchases|Adapty\(\)\.restorePurchases|restore\("):
            add("R11", "HIGH", "3.1.2 / [common]", "No Restore Purchases call found.")
        for f in paywall_files:
            t = sources[f]
            m = re.search(r"signInWithApple|getAppleIDCredential|AppleAuthProvider|reauthenticate|linkWithCredential|Navigator\.[a-zA-Z]+\([^)]*(login|signin|sign_in|auth)", t, re.I)
            if m:
                add("R13", "REVIEW", "2.1(a) / 5.1.1(v)", "Paywall/purchase file triggers login/re-auth. Reviewers were rejected for 'IAP flow redirected to Sign in with Apple'. Logged-in users must purchase without re-auth.",
                    rel(root, f), line_of(t, m.start()))

    # ---------------- R14 frameworks ----------------
    passkit_pods = sorted(p for p in pods if re.match(r"Stripe(ApplePay|PaymentSheet|Payments|Core|UICore)?$|^pay$|Braintree|SquareInAppPayments|Adyen|Checkout", p))
    proximity_pods = sorted(p for p in pods if re.match(r"StripeTerminal|SquareMobilePaymentsSDK|mek_stripe_terminal", p))
    att_pods = sorted(p for p in pods if re.match(r"app_tracking_transparency|FBSDKCoreKit|FBAEMKit|AppsFlyerFramework|Adjust|Google-Mobile-Ads-SDK|AppLovinSDK|UnityAds|IronSourceSDK|Singular|KochavaTracker|TikTokOpenSDK", p))
    linked, app_err = (None, None)
    if app:
        linked, app_err = inspect_app(app)
        if app_err:
            add("R14", "INFO", "-", f"Binary inspection skipped: {app_err}")
    uses_applepay = bool(first(r"ApplePay|applePay|PaymentSheetApplePay|PlatformPay|ApplePayButton"))
    uses_tap = bool(first(r"TapToPay|tapToPay|discoverReaders|LocalMobile"))
    if (linked and "PassKit" in linked) or passkit_pods:
        src = f"linked by {', '.join(linked['PassKit'])}" if linked and "PassKit" in linked else f"pods {', '.join(passkit_pods)}"
        add("R14", "MEDIUM" if uses_applepay else "HIGH", "2.1 Information Needed",
            f"PassKit (Apple Pay) in binary ({src}). " + ("Apple Pay usage found — tell reviewers where." if uses_applepay else "No Apple Pay usage found — remove the SDK or explain in Review Notes."))
    if (linked and "ProximityReader" in linked) or proximity_pods:
        src = f"linked by {', '.join(linked['ProximityReader'])}" if linked and "ProximityReader" in linked else f"pods {', '.join(proximity_pods)}"
        add("R14", "MEDIUM" if uses_tap else "HIGH", "2.1 Information Needed",
            f"ProximityReader (Tap to Pay) in binary ({src}). " + ("Tap to Pay usage found — tell reviewers where." if uses_tap else "No Tap to Pay usage found — remove the SDK or explain in Review Notes."))

    # ---------------- R15 ATT ----------------
    att_in_binary = bool(linked and "AppTrackingTransparency" in linked)
    if has("app_tracking_transparency") or att_in_binary or "NSUserTrackingUsageDescription" in usage_keys:
        hit = first(r"requestTrackingAuthorization")
        if not hit:
            add("R15", "HIGH", "2.1 Information Needed", "ATT framework/usage string present but requestTrackingAuthorization() never called. Either show the prompt or remove ATT + NSUserTrackingUsageDescription and declare no tracking.")
        else:
            f, ln, _ = hit
            t = sources[f]
            ctx = t[max(0, t.rfind("\n", 0, t.find("requestTrackingAuthorization")) - 1500): t.find("requestTrackingAuthorization")]
            if re.search(r"void main\(|Future<void> main\(", ctx) and "addPostFrameCallback" not in ctx:
                add("R15", "HIGH", "2.1 Information Needed", "ATT requested in main() before the app is active — on recent iOS the dialog silently doesn't appear. Request after first frame / on AppLifecycleState.resumed.",
                    rel(root, f), ln)
            else:
                add("R15", "REVIEW", "2.1 Information Needed", "ATT requested here. Verify on a fresh install on the latest iPadOS that the dialog appears, after the app is active and before any tracking SDK initializes.",
                    rel(root, f), ln)
        if not tracking or tracking == ["ATT plugin"]:
            add("R15", "REVIEW", "5.1.2", "ATT is present but no ad/attribution SDK found. If you don't track, remove ATT and declare no tracking in App Privacy.")
    elif tracking:
        add("R15", "HIGH", "5.1.2 / 2.1", f"Tracking/ads SDKs ({', '.join(tracking)}) without ATT. If they track (IDFA, cross-app ads), you must request ATT first.")
    elif att_pods:
        add("R15", "MEDIUM", "2.1", f"Pods that may link AppTrackingTransparency: {', '.join(att_pods)}. Build with --app to confirm.")

    # ---------------- R16 AI ----------------
    if ai_services:
        consent = first(r"consent|i agree|allow.*(ai|openai|gemini)|data (will be|is) sent|shared with|third[- ]party ai")
        names_provider = all(re.search(re.escape(n.split(" ")[0]), all_src, re.I) for n in ai_services)
        sev = "REVIEW" if (consent and names_provider) else "BLOCKER"
        add("R16", sev, "5.1.1(i) + 5.1.2(i)",
            f"App sends data to third-party AI: {', '.join(f'{k} ({v[0]})' for k, v in ai_services.items())}. "
            + ("Consent text found — verify it names the provider, lists the data and appears BEFORE the first request." if sev == "REVIEW"
               else "No consent screen naming the provider found. Apple requires: what data, who receives it, permission before sending."),
            fix="rules.md R16.")
    else:
        add("R16", "INFO", "5.1.2(i)", "No AI SDK/host in the app. ASK the user whether the BACKEND sends user data (text, audio, images) to an AI provider — that also requires in-app consent.")

    # ---------------- R17 / R21 privacy ----------------
    if not profile["privacy_manifest"]:
        add("R17", "HIGH", "5.1.1 / ITMS-91053", "ios/Runner/PrivacyInfo.xcprivacy missing.", fix="rules.md R17.")
    urls = sorted({m.group(0).rstrip(".,;") for _, _, m in grep(URL_RE.pattern)})
    privacy_urls = [u for u in urls if re.search(r"privacy|confidential|privacidad|datenschutz", u, re.I)]
    terms_urls = [u for u in urls if re.search(r"terms|tos|eula|conditions|cgu|legal", u, re.I)]
    if not privacy_urls and not first(r"privacy ?policy|politique de confidentialit"):
        add("R21", "MEDIUM", "5.1.1(i)", "No privacy policy link found in lib/.")

    # ---------------- R18 iPad ----------------
    if ipad:
        o = info.get("UISupportedInterfaceOrientations~ipad", [])
        if not info.get("UIRequiresFullScreen") and len(o) < 4:
            add("R18", "MEDIUM", "2.1 / ITMS-90474", f"iPad supported but UISupportedInterfaceOrientations~ipad has {len(o)} orientations (need 4) and UIRequiresFullScreen not set.",
                "ios/Runner/Info.plist")
        add("R18", "INFO", "2.3.3 / 2.1(a)", "iPad is supported (TARGETED_DEVICE_FAMILY includes 2): upload real 13-inch iPad screenshots and test every flow on an iPad simulator in release mode.")
    elif ipad is False:
        add("R18", "INFO", "2.1(a)", "iPhone-only, but Apple still reviews on iPad in compatibility mode. Test on an iPad simulator anyway.")
    if not first(r"ErrorWidget\.builder"):
        add("R20", "INFO", "2.1(a)", "ErrorWidget.builder not customized: any release-mode build error shows a grey screen (rejected as 'grey screen on home/profile page'). Add a fallback + crash reporting.")
    if not (any(p in direct for p in ("firebase_crashlytics", "sentry_flutter", "bugsnag_flutter", "datadog_flutter_plugin"))):
        add("R20", "INFO", "2.1(a)", "No crash reporting SDK — you won't see crashes the reviewer hits.")

    # ---------------- Data inventory ----------------
    inventory, third_parties = [], set()
    for pkg, (types, party) in SDK_DATA_MAP.items():
        if pkg in direct:
            for t in types:
                inventory.append({"data": t, "source": f"package:{pkg}", "third_party": party})
            if party:
                third_parties.add(party)
    for k in usage_keys:
        if k in PERMISSION_DATA:
            inventory.append({"data": PERMISSION_DATA[k], "source": f"permission:{k}", "third_party": None})
    for ff in form_fields:
        inventory.append({"data": ff["category"], "source": f"form:{ff['field']} ({ff['file']}:{ff['line']})",
                          "third_party": None, "required": ff["looks_required"]})
    for name, src in ai_services.items():
        inventory.append({"data": "User Content sent to AI (confirm types)", "source": src[0], "third_party": name})
        third_parties.add(name)
    for v in tracking:
        if v != "ATT plugin":
            third_parties.add(v)

    findings.sort(key=lambda x: (SEVERITY_ORDER.index(x["severity"]), x["rule"]))
    return {
        "project": str(root),
        "profile": profile,
        "linked_frameworks": linked,
        "findings": findings,
        "permissions": permissions,
        "form_fields": form_fields,
        "ai_services": ai_services,
        "data_inventory": inventory,
        "third_parties": sorted(third_parties),
        "urls_in_app": {"privacy": privacy_urls, "terms": terms_urls},
        "pods_of_interest": {"passkit": passkit_pods, "proximity_reader": proximity_pods, "att": att_pods},
    }


def render(r):
    p = r["profile"]
    out = ["# App Store review pre-flight", "", f"Project: `{r['project']}`", "", "## App profile", ""]
    yn = lambda b: "yes" if b else ("no" if b is False else "unknown")
    out += [
        f"- Subscriptions / IAP: **{yn(p['subscriptions_or_iap'])}** {('(' + ', '.join(p['iap_stack']) + ')') if p['iap_stack'] else ''}",
    ]
    if p["mentions_subscription_without_iap_package"]:
        out.append("  - ⚠️ Code mentions subscriptions/premium but no IAP package — how is it sold?")
    out += [
        f"- Accounts: **{yn(p['has_accounts'])}** · social login: {', '.join(p['social_login']) or 'none'} · Sign in with Apple: **{yn(p['sign_in_with_apple'])}**",
        f"- External payment SDKs: {', '.join(p['external_payment_sdks']) or 'none'}",
        f"- Third-party AI in app: {', '.join(p['ai_services_in_app']) or 'none found (ask about backend)'}",
        f"- Tracking/ads SDKs: {', '.join(p['tracking_sdks']) or 'none'}",
        f"- iPad supported: **{yn(p['ipad_supported'])}** (TARGETED_DEVICE_FAMILY {', '.join(p['targeted_device_family']) or '?'})",
        f"- Privacy manifest: {yn(p['privacy_manifest'])} · Dart files scanned: {p['dart_files_scanned']}",
    ]
    if r["linked_frameworks"] is not None:
        out.append(f"- Linked frameworks (binary): {', '.join(sorted(r['linked_frameworks'])) or 'none of interest'}")
    out += ["", "## Findings", ""]
    counts = {}
    for f in r["findings"]:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    out.append(" · ".join(f"{s}: {counts.get(s, 0)}" for s in SEVERITY_ORDER))
    out.append("")
    for f in r["findings"]:
        loc = f" — `{f['file']}{':' + str(f['line']) if f['line'] else ''}`" if f["file"] else ""
        out.append(f"- **[{f['severity']}] {f['rule']}** ({f['guideline']}){loc}: {f['message']}" + (f" _Fix: {f['fix']}_" if f.get("fix") else ""))
    out += ["", "## Data inventory (for privacy policy / App Privacy)", ""]
    for d in r["data_inventory"]:
        tp = f" → {d['third_party']}" if d.get("third_party") else ""
        req = " (required)" if d.get("required") else ""
        out.append(f"- {d['data']}{req} — {d['source']}{tp}")
    out += ["", f"Third parties: {', '.join(r['third_parties']) or 'none detected'}",
            f"Privacy URLs in app: {', '.join(r['urls_in_app']['privacy']) or 'none'}",
            f"Terms URLs in app: {', '.join(r['urls_in_app']['terms']) or 'none'}", ""]
    out.append("_Heuristic scan. Confirm REVIEW items in code; see references/rules.md for each rule. Manual checklist is in rules.md._")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--app", help="Built .ipa or Runner.app to inspect linked frameworks (macOS)")
    ap.add_argument("--json", help="Write full results as JSON to this path")
    a = ap.parse_args()
    r = scan(a.project, a.app)
    print(render(r))
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=2, default=str))
        print(f"\nJSON written to {a.json}")
    sys.exit(1 if any(f["severity"] == "BLOCKER" for f in r["findings"]) else 0)


if __name__ == "__main__":
    main()
