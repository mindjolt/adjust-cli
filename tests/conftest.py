import json
import os
from typing import Iterator
import pytest
import random

from click.testing import CliRunner
from requests_mock import Mocker

from adjust.api.api import AdjustAPI
from adjust.api.model import App, AppsResponse, Callback, RawCallback, User
from adjust.snapshot import Snapshot, normalize_snapshot
from .utils import (
    HelpCommand,
    HelpOption,
    HelpOutput,
    random_app,
    random_callback,
    random_callbacks,
    random_string,
    random_user,
)


@pytest.fixture
def simulate_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.isatty", lambda n: True)


@pytest.fixture
def password() -> str:
    return random_string(8)


@pytest.fixture
def user() -> User:
    return random_user()


@pytest.fixture
def apps(requests_mock: Mocker) -> dict[str, App]:
    apps = [random_app() for _ in range(random.randint(8, 16))]
    response = AppsResponse.parse_obj({"apps": apps, "urls": {}, "page": {"position": 0}})
    requests_mock.get(
        "https://api.adjust.com/dashboard/api/apps",
        text=response.json(),
    )
    return {app.token: app for app in apps}


@pytest.fixture
def app() -> App:
    return random_app()


@pytest.fixture
def raw_callback() -> RawCallback:
    return random_callback(None)


@pytest.fixture
def callback(raw_callback: RawCallback) -> Callback:
    return raw_callback.to_callback()


@pytest.fixture
def apps_with_callbacks(requests_mock: Mocker, apps: dict[str, App]) -> dict[App, list[RawCallback]]:
    rv = {app: random_callbacks(random.randint(0, 4)) for app in apps.values()}
    for app, callbacks in rv.items():
        requests_mock.get(
            f"https://api.adjust.com/dashboard/api/apps/{app.token}/callbacks",
            text=json.dumps([cb.dict() for cb in callbacks]),
        )
    return rv


@pytest.fixture
def api(requests_mock: Mocker, user: User, password: str) -> AdjustAPI:
    requests_mock.post(
        "https://api.adjust.com/accounts/users/sign_in",
        text=user.json(),
    )
    return AdjustAPI(email=user.email, password=password)


@pytest.fixture
def snapshot(apps_with_callbacks: dict[App, list[RawCallback]]) -> Snapshot:
    rv = {app.token: [cb.to_callback() for cb in callbacks] for app, callbacks in apps_with_callbacks.items()}
    return normalize_snapshot(rv)


@pytest.fixture
def runner(requests_mock: Mocker, user: User) -> CliRunner:
    requests_mock.post(
        "https://api.adjust.com/accounts/users/sign_in",
        text=user.json(),
    )
    return CliRunner()


@pytest.fixture
def cli_help() -> HelpOutput:
    return HelpOutput(
        help="Adjust API CLI",
        options=[
            HelpOption(names=["--help"], help="Show this message and exit."),
        ],
        commands=[
            HelpCommand(name="snapshot", help="Manage Adjust callback snapshots"),
        ],
    )


@pytest.fixture
def callbacks_snapshot_help() -> HelpOutput:
    return HelpOutput(
        help="Manage Adjust callback snapshots",
        options=[HelpOption(names=["--help"], help="Show this message and exit.")],
        commands=[
            HelpCommand(name="create", help="Create a local snapshot of all Adjust callbacks"),
            HelpCommand(name="modify", help="Modify local snapshot"),
            HelpCommand(name="restore", help="Restore Adjust callbacks from local snapshot"),
        ],
    )


@pytest.fixture
def snapshot_create_help() -> HelpOutput:
    return HelpOutput(
        help="Create a local snapshot of all Adjust callbacks",
        options=[
            HelpOption(names=["-s", "--snapshot DIRECTORY"], help="Snapshot path  [default: snapshot]"),
            HelpOption(names=["--non-interactive"], help="Allow interaction with user"),
            HelpOption(names=["-f", "--force"], help="Overwrite existing snapshot"),
            HelpOption(names=["--help"], help="Show this message and exit."),
        ],
    )


@pytest.fixture
def snapshot_restore_help() -> HelpOutput:
    return HelpOutput(
        help="Restore Adjust callbacks from local snapshot",
        options=[
            HelpOption(names=["-s", "--snapshot DIRECTORY"], help="Snapshot path  [default: snapshot]"),
            HelpOption(names=["-n", "--dry-run"], help="Do not invoke the Adjust API, only simulate what"),
            HelpOption(names=["--help"], help="Show this message and exit."),
        ],
    )


@pytest.fixture
def snapshot_modify_help() -> HelpOutput:
    return HelpOutput(
        help="Modify local snapshot",
        options=[
            HelpOption(names=["-s", "--snapshot DIRECTORY"], help="Snapshot path  [default: snapshot]"),
            HelpOption(names=["--having-placeholder PH"], help="Only modify callbacks having placeholder PH"),
            HelpOption(names=["--having-app NAME"], help="Only modify apps named NAME"),
            HelpOption(names=["--having-app-token TOKEN"], help="Only modify apps with token TOKEN"),
            HelpOption(names=["--having-domain DOMAIN"], help="Only modify callbacks whose URL domain is DOMAIN"),
            HelpOption(names=["--having-path PATH"], help="Only modify callbacks whose URL is PATH"),
            HelpOption(names=["--matching-placeholder REGEX"], help="Only modify callbacks having placeholders"),
            HelpOption(names=["--matching-app REGEX"], help="Only modify apps whose name match REGEX"),
            HelpOption(names=["--matching-domain REGEX"], help="Only modify callbacks whose URL domain matches"),
            HelpOption(names=["--matching-path REGEX"], help="Only modify callbacks whose URL matches REGEX"),
            HelpOption(names=["-a", "--add-placeholder PH"], help="Add placeholder PH to all matching callbacks"),
            HelpOption(names=["-n", "--dry-run"], help="Do not update the snapshot, only simulate what"),
            HelpOption(names=["--help"], help="Show this message and exit."),
        ],
        commands=[],
    )
