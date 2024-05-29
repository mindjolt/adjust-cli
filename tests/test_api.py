import os
import pytest

from requests_mock.mocker import Mocker
from adjust.api import AdjustAPI
from adjust.api.model import App, Callback, User
from adjust.snapshot import Snapshot


def test_email_required(requests_mock: Mocker) -> None:
    os.environ.pop("ADJUST_EMAIL", None)
    with pytest.raises(ValueError, match="Email not provided"):
        AdjustAPI()


def test_password_required(requests_mock: Mocker) -> None:
    os.environ.pop("ADJUST_PASSWORD", None)
    with pytest.raises(ValueError, match="Password not provided"):
        AdjustAPI(email="name@email.com")


def test_sign_in(requests_mock: Mocker, user: User, password: str) -> None:
    requests_mock.post(
        "https://api.adjust.com/accounts/users/sign_in",
        text=user.json(),
    )
    api = AdjustAPI(email=user.email, password=password)
    assert user == api.user()
    assert requests_mock.request_history[0].json() == dict(user=dict(email=user.email, password=password, remember_me=True))


def test_sign_in_from_env(requests_mock: Mocker, user: User, password: str) -> None:
    os.environ["ADJUST_EMAIL"] = user.email
    os.environ["ADJUST_PASSWORD"] = password
    requests_mock.post(
        "https://api.adjust.com/accounts/users/sign_in",
        text=user.json(),
    )
    api = AdjustAPI()
    assert user == api.user()
    assert requests_mock.request_history[0].json() == dict(user=dict(email=user.email, password=password, remember_me=True))


def test_apps(api: AdjustAPI, apps: dict[str, App]) -> None:
    assert list(apps.values()) == api.apps


def test_callbacks(api: AdjustAPI, snapshot: Snapshot) -> None:
    for app_token, callbacks in snapshot.items():
        assert callbacks == api.callbacks(app_token)


def test_update_callbacks(requests_mock: Mocker, api: AdjustAPI, app: App, callback: Callback) -> None:
    requests_mock.put(
        f"https://api.adjust.com/dashboard/api/apps/{app.token}/event_types/{callback.id}/callback",
        status_code=204,
    )
    api.update_callback(app, callback)
    request = next(r for r in requests_mock.request_history if r.method == "PUT")
    assert request.json() == dict(callback_url=callback.url)
