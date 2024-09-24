from __future__ import annotations

import bisect
from datetime import date, datetime
from typing import Literal, Type, TypeVar
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pydantic import BaseModel, Extra, Field


class PlaceholderType(BaseModel):
    label: str
    value: str


class Placeholder(BaseModel):
    category: str
    placeholder: str
    content: str
    example: str
    dataType: str
    impression: bool  # Impression
    click: bool  # Click
    install: bool  # Install
    session: bool  # Session
    reattribution: bool  # reattribution
    event: bool  # In-app event
    uninstall: bool  # Uninstall
    reinstall: bool  # Reinstall
    reattributionReinstall: bool  # Reattribution reinstall
    adSpend: bool  # Ad spend
    gdpr: bool  # Erased user (GDPR)
    clients: bool
    dynamicPartners: bool
    modulePartners: bool
    sanClick: bool  # SAN click
    sanImpression: bool  # SAN impression
    adRevenue: bool  # Ad revenue
    subscription: bool  # Subscription
    attUpdate: bool  # ATT status update (iOS)

    attributionUpdate: bool  # Attribution update
    skCvUpdate: bool  # SkAdNetwork CV update
    skEvent: bool  # SkAdNetwork event
    skInstall: bool  # SkAdNetwork install
    skInstallDirect: bool  # SkAdNetwork direct install
    skQualifier: bool  # SKAdNetwork qualifier
    availableAs: list[PlaceholderType]
    unavailableAs: list[PlaceholderType]


class App(BaseModel):
    id: int
    name: str
    token: str
    app_token: str  # wv12z93syz35
    currency: Currency
    default_store_app_id: str | None  # com.acme.game
    integration_dates: IntegrationDates
    permissions: Permissions
    platforms: Platforms
    start_date: date
    default_attribution_platform: str  # mobile_app
    is_ctv: bool
    is_child_directed: bool
    fraud_prevention_settings: FraudPreventionSettings

    def __hash__(self) -> int:
        return hash(self.token)

    def __str__(self) -> str:
        return f"{self.name} ({self.token})"


class Currency(BaseModel):
    name: str  # United States Dollar
    symbol: str  # $
    iso_code: str  # USD


class IntegrationDates(BaseModel):
    android: date | None
    android_tv: date | None = Field(alias="android-tv")
    ios: date | None
    linux: date | None
    unknown: date | None
    windows: date | None
    windows_phone: date | None = Field(alias="windows-phone")


class Permissions(BaseModel):
    generate_report: bool = False
    read_statistics: bool = False
    create_tracker: bool = False
    update_settings: bool = False
    update_custom_twitter_permissions: bool = False


class Platforms(BaseModel):
    android: Platform
    ios: iOSPlatform
    windows: Platform
    windows_phone: Platform = Field(alias="windows-phone")

    class Config:
        allow_population_by_field_name = True


class Platform(BaseModel):
    configured: bool
    store: Literal["amazon", "google", "itunes", "windows"] | None
    app_id: str | None


class iOSPlatform(Platform):
    app_state: Literal["not_verified", "verified"] | None
    ios_bundle_id: str | None


class FraudPreventionSettings(BaseModel):
    distribution_filter: Literal["advanced", "standard"] | None
    show_invalid_signature: bool = False
    filter_anonymous_traffic: bool = False
    filter_engagement_injection: bool = False
    filter_too_many_engagements: bool = False


class AppsResponse(BaseModel):
    apps: list[App]
    urls: Urls
    page: Page

    class Config:
        extra = Extra.forbid


class Urls(BaseModel):
    class Config:
        extra = Extra.forbid


class Page(BaseModel):
    position: int

    class Config:
        extra = Extra.forbid


App.update_forward_refs()
AppsResponse.update_forward_refs()
Platforms.update_forward_refs()


CallbackType = Literal[
    "rejected_reattribution",
    "reattribution",
    "att_consent",
    "click",
    "gdpr_forget_device",
    "subscription_renewal",
    "cost_update",
    "install",
    "sk_event",
    "reattribution_reinstall",
    "subscription_renewal_from_billing_retry",
    "subscription_entered_billing_retry",
    "subscription",
    "session",
    "sk_cv_update",
    "subscription_cancellation",
    "san_click",
    "subscription_activation",
    "impression",
    "subscription_reactivation",
    "ad_revenue",
    "global",
    "sk_install_direct",
    "uninstall",
    "sk_install",
    "reinstall",
    "rejected_install",
    "attribution_update",
    "san_impression",
    "sk_qualifier",
    "subscription_first_conversion",
]


class RawCallback(BaseModel):
    id: CallbackType | int
    name: str
    url: str | None
    custom: bool
    token: str | None

    @property
    def index(self) -> str:
        return self.id if not isinstance(self.id, int) else self.name

    def to_callback(self) -> Callback:
        urls = [CallbackURL.from_url(u) for u in self.url.split()] if self.url else []
        return Callback(
            id=self.id,
            type="event" if isinstance(self.id, int) else self.id,
            name=self.name,
            urls=urls,
            custom=self.custom,
            token=self.token,
        )


class Callback(BaseModel):
    id: CallbackType | int
    type: str
    name: str
    urls: list[CallbackURL]
    custom: bool
    token: str | None

    @property
    def url(self) -> str | None:
        return " ".join(u.url for u in self.urls) if self.urls else None

    @property
    def unique_name(self) -> str:
        """Returns the callback type for regular callbacks or the event name
        for custom callbacks.


        Returns:
            str: the callback type or the event name if this is a custom callback
        """
        return self.id if not isinstance(self.id, int) else self.name


S = TypeVar("S", bound="CallbackURL")


class CallbackURL(BaseModel):
    scheme: str
    netloc: str
    path: str
    query: dict[str, str]
    fragment: str = ""
    placeholders: list[str]

    @classmethod
    def from_url(cls: Type[S], url_string: str) -> S:
        def is_placeholder(e: tuple[str, str]) -> bool:
            return e[1] == f"{{{e[0]}}}"

        url = urlsplit(url_string)
        assert "://" not in url.query, f"Invalid URL: {url_string}"
        qsl = parse_qsl(url.query, keep_blank_values=True)
        query = sorted((e for e in qsl if not is_placeholder(e)), key=lambda e: e[0])
        placeholders = sorted(e[0] for e in qsl if is_placeholder(e))
        return cls(
            scheme=url.scheme,
            netloc=url.netloc,
            path=url.path,
            query=query,
            fragment=url.fragment,
            placeholders=placeholders,
        )

    @property
    def url(self) -> str:
        def to_tuple(placeholder: str) -> tuple[str, str]:
            return (placeholder, f"{{{placeholder}}}")

        qsl1 = [(k, v) for k, v in self.query.items()]
        qsl2 = [to_tuple(p) for p in sorted(self.placeholders)]
        query = urlencode(qsl1 + qsl2, safe="/{}")
        return urlunsplit((self.scheme, self.netloc, self.path, query, self.fragment))

    def add_placeholder(self, placeholder: str) -> None:
        index = bisect.bisect_left(self.placeholders, placeholder)
        if index == len(self.placeholders) or self.placeholders[index] != placeholder:
            self.placeholders.insert(index, placeholder)


Callback.update_forward_refs()


class Event(BaseModel):
    id: int
    name: str
    token: str
    callback_url: str | None
    unique: bool | None
    urls: EventURLs
    autogenerated: bool
    archived: bool
    first_skad_data: date | None


class EventURLs(BaseModel):
    archive: str | None = None
    unarchive: str | None = None


Event.update_forward_refs()


class EventsResponse(BaseModel):
    events: list[Event]


class User(BaseModel):
    id: int
    email: str
    name: str | None
    main_account_id: int
    main_account_type: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    authentication_token: str
    locale: str  # 'en'
    uses_next: bool
    api_access: None
    first_name: str
    last_name: str
    super_admin: bool
    salesforce_sync_failed: bool
    ct_role: None
    timezone_id: int
    uses_dash: bool
    sso: bool
    direct_otp: None
    direct_otp_sent_at: None
    encrypted_otp_secret_key: None
    encrypted_otp_secret_key_iv: None
    encrypted_otp_secret_key_salt: None

class UserToken(BaseModel):
    id: int
    email: str
    name: str | None