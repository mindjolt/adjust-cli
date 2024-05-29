import datetime
import os
import random
import string

from pydantic import BaseModel
from typing import Optional
from urllib.parse import urlunsplit

from adjust.api.model import App, RawCallback, User


def random_string(length: int) -> str:
    letters = string.ascii_letters
    return "".join(random.choice(letters) for i in range(length))


def random_domain() -> str:
    return f"{random_string(10)}.{random.choice(['com', 'org', 'net', 'io'])}"


def random_email() -> str:
    return f"{random_string(8)}@{random_domain()}"


def random_timestamp(a: int, b: int) -> datetime.datetime:
    return datetime.datetime.now() + datetime.timedelta(seconds=random.randint(a, b))


def random_app() -> App:
    token = random_string(12)
    app_id = str(random.randint(0, 10_000_000_000))
    return App.parse_obj(
        {
            "id": random.randint(1, 100_000),
            "name": random_string(10),
            "token": token,
            "start_date": random_timestamp(-365 * 86400, -30 * 86400).date().isoformat(),
            "default_store_app_id": app_id,
            "integration_dates": {
                "ios": random_timestamp(-30 * 86400, -10 * 86400).date().isoformat(),
                "android": random_timestamp(-30 * 86400, -10 * 86400).date().isoformat(),
                "windows": random_timestamp(-30 * 86400, -10 * 86400).date().isoformat(),
            },
            "default_attribution_platform": "mobile_app",
            "is_ctv": False,
            "is_console": False,
            "is_pc": False,
            "is_mobile": True,
            "is_web": False,
            "is_child_directed": False,
            "no_eea_users": False,
            "fraud_prevention_settings": {
                "distribution_filter": "standard",
                "show_invalid_signature": True,
                "filter_anonymous_traffic": True,
                "filter_engagement_injection": True,
                "filter_too_many_engagements": True,
            },
            "ad_revenue_max_amount": None,
            "app_token": token,
            "platforms": {
                "android": {"configured": True, "store": "google", "app_id": random_domain()},
                "ios": {
                    "configured": True,
                    "store": "itunes",
                    "app_id": app_id,
                    "app_state": "not_verified",
                    "ios_bundle_id": random_domain(),
                },
                "windows": {"configured": False},
                "windows-phone": {"configured": False},
                "web": {"configured": False},
            },
            "permissions": {
                "generate_report": True,
                "read_statistics": True,
                "create_tracker": True,
                "update_settings": True,
                "update_custom_twitter_permissions": True,
            },
            "currency": {"name": "United States Dollar", "symbol": "$", "iso_code": "USD"},
        },
    )


def random_user() -> User:
    return User.parse_obj(
        {
            "id": random.randint(1, 1000),
            "email": random_email(),
            "name": None,
            "main_account_id": random.randint(1, 1000),
            "main_account_type": "Account",
            "created_by": None,
            "created_at": random_timestamp(-30 * 86400, -10 * 86400).isoformat(),
            "updated_at": random_timestamp(-10 * 86400, -1 * 86400).isoformat(),
            "authentication_token": random_string(20),
            "locale": "en",
            "uses_next": False,
            "api_access": None,
            "first_name": "Reader",
            "last_name": "Account",
            "super_admin": False,
            "salesforce_sync_failed": False,
            "ct_role": None,
            "timezone_id": 172,
            "uses_dash": True,
            "sso": False,
            "direct_otp": None,
            "direct_otp_sent_at": None,
            "encrypted_otp_secret_key": None,
            "encrypted_otp_secret_key_iv": None,
            "encrypted_otp_secret_key_salt": None,
            "agency": False,
        }
    )


def random_callbacks(callback_count: int, custom_count: int = 0) -> list[RawCallback]:
    sampled_names = random.sample(list(callback_names.keys()), callback_count)
    sampled_custom = [random.randint(0, 10_000_000) for _ in range(custom_count)]
    generated = [random_callback(name) for name in sampled_names + sampled_custom]
    return sorted(generated, key=lambda c: c.index)


def random_callback_url(placeholder_count: int) -> str:
    placeholders = random.sample(placeholder_names, placeholder_count)
    scheme = random.choice(["http", "https"])
    netloc = random_domain()
    path = "/".join(random_string(10) for _ in range(random.randint(1, 4)))
    query = "&".join(f"{p}={{{p}}}" for p in placeholders)
    return urlunsplit((scheme, netloc, path, query, ""))


def random_callback(id: Optional[str | int]) -> RawCallback:
    id = id or random.choice(list(callback_names.keys()))
    name = callback_names.get(id) if isinstance(id, str) else random_string(10)
    return RawCallback.parse_obj(
        {
            "id": id,
            "name": name,
            "url": random_callback_url(random.randint(2, 4)),
            "custom": isinstance(id, int),
        }
    )


callback_names = {
    "install": "Install",
    "reattribution": "Reattribution",
    "click": "Click",
    "session": "Session",
    "global": "Global",
    "rejected_install": "Rejected Install",
    "impression": "Impression",
    "attribution_update": "Attribution Update",
    "rejected_reattribution": "Rejected Reattribution",
    "uninstall": "Uninstall",
    "reinstall": "Reinstall",
    "reattribution_reinstall": "Reattribution Reinstall",
    "cost_update": "Cost Update",
    "att_consent": "Att Consent",
    "gdpr_forget_device": "Gdpr Forget Device",
    "san_impression": "San Impression",
    "san_click": "San Click",
    "ad_revenue": "Ad Revenue",
    "sk_install": "Sk Install",
    "sk_event": "Sk Event",
    "sk_qualifier": "Sk Qualifier",
    "sk_cv_update": "Sk Cv Update",
    "sk_install_direct": "Sk Install Direct",
    "subscription": "Subscription",
    "subscription_activation": "Subscription Activation",
    "subscription_first_conversion": "Subscription First Conversion",
    "subscription_cancellation": "Subscription Cancellation",
    "subscription_renewal": "Subscription Renewal",
    "subscription_reactivation": "Subscription Reactivation",
    "subscription_entered_billing_retry": "Subscription Entered Billing Retry",
    "subscription_renewal_from_billing_retry": "Subscription Renewal From Billing Retry",
    "256328375": "S2SRevenue",
    "1549856936": "Sale",
    "103329361": "Signup",
    "1621060568": "Signup2",
    "282965313": "Social",
}

placeholder_names = [
    "activity_kind",
    "adgroup_name",
    "adid",
    "android_id",
    "api_level",
    "app_id",
    "app_name",
    "app_version",
    "app_version_raw",
    "app_version_short",
    "attribution_expires_at",
    "attribution_ttl",
    "callback_ttl",
    "campaign_name",
    "city",
    "click_attribution_window",
    "click_referer",
    "click_time",
    "connection_type",
    "conversion_duration",
    "cost_amount",
    "cost_currency",
    "cost_id_md5",
    "cost_type",
    "country",
    "country_subdivision",
    "cpu_type",
    "created_at",
    "created_at_milli",
    "creative_name",
    "dbm_campaign_type",
    "dbm_creative_id",
    "dbm_exchange_id",
    "dbm_external_customer_id",
    "dbm_insertion_order_id",
    "dbm_line_item_id",
    "dbm_line_item_name",
    "dcm_campaign_type",
    "dcm_creative_id",
    "dcm_external_customer_id",
    "dcm_placement_id",
    "dcm_placement_name",
    "dcm_site_id",
    "dcp_adset_id",
    "dcp_adset_name",
    "dcp_bundle_id",
    "dcp_campaign_id",
    "dcp_creative_id",
    "dcp_creative_size",
    "dcp_creative_type",
    "dcp_custom_field_1",
    "dcp_custom_field_2",
    "dcp_custom_field_3",
    "dcp_custom_field_4",
    "dcp_custom_field_5",
    "dcp_developer_id",
    "dcp_developer_name",
    "dcp_exchange",
    "dcp_placement",
    "dcp_promotion_name",
    "dcp_subpub_name",
    "dcp_subpubid",
    "deeplink",
    "device_atlas_id",
    "device_manufacturer",
    "device_name",
    "device_type",
    "engagement_time",
    "environment",
    "external_device_id_md5",
    "fb_install_referrer",
    "fb_install_referrer_account_id",
    "fb_install_referrer_ad_id",
    "fb_install_referrer_ad_objective_name",
    "fb_install_referrer_adgroup_id",
    "fb_install_referrer_adgroup_name",
    "fb_install_referrer_campaign_group_id",
    "fb_install_referrer_campaign_group_name",
    "fb_install_referrer_campaign_id",
    "fb_install_referrer_campaign_name",
    "fb_install_referrer_publisher_platform",
    "fingerprint_attribution_window",
    "fire_adid",
    "first_tracker",
    "first_tracker_name",
    "gclid",
    "gmp_product_type",
    "google_ads_ad_type",
    "google_ads_adgroup_id",
    "google_ads_adgroup_name",
    "google_ads_campaign_id",
    "google_ads_campaign_name",
    "google_ads_campaign_type",
    "google_ads_creative_id",
    "google_ads_external_customer_id",
    "google_ads_keyword",
    "google_ads_matchtype",
    "google_ads_network_subtype",
    "google_ads_network_type",
    "google_ads_placement",
    "google_ads_video_id",
    "gps_adid",
    "hardware_name",
    "iad_ad_id",
    "iad_conversion_type",
    "iad_creative_set_id",
    "iad_creative_set_name",
    "iad_keyword_matchtype",
    "idfa",
    "idfv",
    "impression_attribution_window",
    "impression_based",
    "impression_time",
    "install_begin_time",
    "install_finish_time",
    "installed_at",
    "is_imported",
    "is_organic",
    "is_reattributed",
    "is_s2s_engagement_based",
    "isp",
    "label",
    "language",
    "lifetime_session_count",
    "mac_md5",
    "match_type",
    "mcc",
    "mnc",
    "network_name",
    "network_type",
    "nonce",
    "oaid",
    "os_name",
    "os_version",
    "partner_parameters",
    "platform",
    "postal_code",
    "probmatching_attribution_window",
    "publisher_parameters",
    "push_token",
    "random_user_id",
    "received_at",
    "referral_time",
    "referrer",
    "reftag",
    "reftags",
    "region",
    "rejection_reason",
    "reporting_cost",
    "san_engagement_times",
    "sdk_version",
    "search_term",
    "secret_id",
    "session_count",
    "store",
    "timezone",
    "tracker",
    "tracker_name",
    "tracking_enabled",
    "tracking_limited",
    "tweet_id",
    "twitter_line_item_id",
    "web_uuid",
    "within_callback_ttl",
]


class HelpOption(BaseModel):
    names: list[str]
    help: str


class HelpCommand(BaseModel):
    name: str
    help: str


class HelpOutput(BaseModel):
    help: str = ""
    options: list[HelpOption] = []
    commands: list[HelpCommand] = []


def parse_help(result: str) -> HelpOutput:
    updating: Optional[str] = None
    rv = HelpOutput()
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Usage:"):
            updating = "help"
        elif line.startswith("Options:"):
            updating = "options"
        elif line.startswith("Commands:"):
            updating = "commands"
        elif updating:
            if updating == "help":
                if rv.help:
                    rv.help += "\n"
                rv.help += line
            parts = line.split("  ", 1)
            if len(parts) != 2:
                continue
            elif updating == "options":
                rv.options.append(HelpOption(names=parts[0].split(", "), help=parts[1].strip()))
            elif updating == "commands":
                rv.commands.append(HelpCommand(name=parts[0], help=parts[1].strip()))
    return rv


def recursive_directory_listing(path: str) -> dict[str, str]:
    import hashlib

    files = {}
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            md5_hash = hashlib.md5(open(file_path, "rb").read()).hexdigest()
            relative_path = os.path.relpath(file_path, path)
            files[relative_path] = md5_hash
    return files
