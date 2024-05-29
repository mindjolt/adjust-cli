import os
import pytest
import random
import re

from click.testing import CliRunner, Result
from contextlib import contextmanager
from requests_mock.mocker import Mocker
from typing import Callable, Iterator

from adjust.api.model import App, Callback, CallbackURL
from adjust.cli import cli
from adjust.snapshot import Snapshot, snapshot_callback_count, snapshot_load, snapshot_save

from .utils import HelpOutput, parse_help, random_string, recursive_directory_listing


def test_help(requests_mock: Mocker, runner: CliRunner, cli_help: HelpOutput) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert not requests_mock.request_history
    assert cli_help == parse_help(result.output)


def test_argless(requests_mock: Mocker, runner: CliRunner, cli_help: HelpOutput) -> None:
    result = runner.invoke(cli)
    assert result.exit_code == 0
    assert not requests_mock.request_history
    assert cli_help == parse_help(result.output)


def test_callbacks_snapshot_help(requests_mock: Mocker, runner: CliRunner, callbacks_snapshot_help: HelpOutput) -> None:
    result = runner.invoke(cli, ["snapshot", "--help"])
    assert result.exit_code == 0
    assert not requests_mock.request_history
    assert callbacks_snapshot_help == parse_help(result.output)


def test_snapshot_create_help(requests_mock: Mocker, runner: CliRunner, snapshot_create_help: HelpOutput) -> None:
    result = runner.invoke(cli, ["snapshot", "create", "--help"])
    assert result.exit_code == 0
    assert not requests_mock.request_history
    assert snapshot_create_help == parse_help(result.output)


def test_snapshot_restore_help(requests_mock: Mocker, runner: CliRunner, snapshot_restore_help: HelpOutput) -> None:
    result = runner.invoke(cli, ["snapshot", "restore", "--help"])
    assert result.exit_code == 0
    assert not requests_mock.request_history
    assert snapshot_restore_help == parse_help(result.output)


def test_snapshot_modify_help(requests_mock: Mocker, runner: CliRunner, snapshot_modify_help: HelpOutput) -> None:
    result = runner.invoke(cli, ["snapshot", "modify", "--help"])
    assert result.exit_code == 0
    assert not requests_mock.request_history
    assert snapshot_modify_help == parse_help(result.output)


def test_snapshot_create(
    runner: CliRunner,
    snapshot: Snapshot,
    tmp_path: str,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["snapshot", "create", "-s", "output"])
        num_callbacks = snapshot_callback_count(snapshot)
        assert f"✅ Done. Retrieved {num_callbacks} callbacks." in result.output
        assert result.exit_code == 0
        assert os.path.exists("output")
        created_snapshot = snapshot_load("output")
        assert created_snapshot == snapshot


def test_snapshot_create_already_exists(
    runner: CliRunner,
    tmp_path: str,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        os.makedirs("snapshot")
        result = runner.invoke(cli, ["snapshot", "create"])
        assert result.exit_code == 1
        assert "⛔️ Snapshot path `snapshot` already exists. Use --force to overwrite." in result.output


def test_snapshot_create_already_exists_reply_no(
    runner: CliRunner,
    tmp_path: str,
    simulate_tty: None,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        os.makedirs("snapshot")
        result = runner.invoke(cli, ["snapshot", "create"], input="n\n")
        assert result.exit_code == 1
        assert "⚠️ Snapshot path `snapshot` already exists. Overwrite?" in result.output


def test_snapshot_create_already_exists_reply_yes(
    runner: CliRunner,
    snapshot: Snapshot,
    tmp_path: str,
    simulate_tty: None,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        num_callbacks = snapshot_callback_count(snapshot)
        os.makedirs("snapshot")
        result = runner.invoke(cli, ["snapshot", "create"], input="y\n")
        assert result.exit_code == 0
        assert "⚠️ Snapshot path `snapshot` already exists. Overwrite?" in result.output
        assert "⬇️  Creating Snapshot: 100%" in repr(result.output)
        assert f"✅ Done. Retrieved {num_callbacks} callbacks." in result.output
        saved_snapshot = snapshot_load("snapshot")
        assert saved_snapshot == snapshot


def test_snapshot_create_already_exists_forced(
    runner: CliRunner,
    snapshot: Snapshot,
    tmp_path: str,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        snapshot_save("snapshot2", snapshot)
        os.makedirs("snapshot")
        result = runner.invoke(cli, ["snapshot", "create", "-f"])
        num_callbacks = snapshot_callback_count(snapshot)
        assert result.exit_code == 0
        assert f"✅ Done. Retrieved {num_callbacks} callbacks." in result.output
        listing1 = recursive_directory_listing("snapshot")
        listing2 = recursive_directory_listing("snapshot2")
        assert listing1 == listing2


def test_snapshot_restore(
    requests_mock: Mocker,
    runner: CliRunner,
    snapshot: Snapshot,
    tmp_path: str,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        for app_token, callbacks in snapshot.items():
            for callback in callbacks:
                for url in callback.urls:
                    url.add_placeholder("new_placeholder")
                requests_mock.put(
                    f"https://api.adjust.com/dashboard/api/apps/{app_token}/event_types/{callback.id}/callback",
                    status_code=204,
                )
        snapshot_save("snapshot", snapshot)
        result = runner.invoke(cli, ["snapshot", "restore"])
        num_callbacks = snapshot_callback_count(snapshot)
        assert result.exit_code == 0
        assert f"✅ Done. Updated {num_callbacks} callbacks." in result.output
        assert sum(1 for h in requests_mock.request_history if h.method == "PUT") == num_callbacks
        for request in requests_mock.request_history:
            if request.method == "PUT":
                match = re.match(r"/dashboard/api/apps/(.+)/event_types/(.+)/callback", request.path)
                assert match, request.path
                app_token, callback_id = match.groups()
                callback = next(cb for cb in snapshot[app_token] if str(cb.id) == callback_id)
                assert request.json() == dict(callback_url=callback.url)


def test_snapshot_restore_no_changes(
    requests_mock: Mocker,
    runner: CliRunner,
    snapshot: Snapshot,
    tmp_path: str,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        snapshot_save("snapshot", snapshot)
        result = runner.invoke(cli, ["snapshot", "restore"])
        assert result.exit_code == 0
        assert "✅ Done. Updated 0 callbacks." in result.output
        assert sum(1 for h in requests_mock.request_history if h.method == "PUT") == 0


def test_snapshot_restore_doesnt_exist(
    requests_mock: Mocker,
    runner: CliRunner,
    tmp_path: str,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["snapshot", "restore"])
        assert result.exit_code == 2
        assert "Directory 'snapshot' does not exist." in result.output
        assert sum(1 for h in requests_mock.request_history if h.method == "PUT") == 0


class Counters:
    def __init__(self) -> None:
        self.seen_apps: set[str] = set()
        self.seen_callbacks: set[str] = set()
        self.urls = 0

    def update(self, app_token: str, callback: Callback) -> None:
        self.seen_apps.add(app_token)
        self.seen_callbacks.add(f"{app_token}/{callback.id}")
        self.urls += 1

    @property
    def apps(self) -> int:
        return len(self.seen_apps)

    @property
    def callbacks(self) -> int:
        return len(self.seen_callbacks)

    @property
    def expected_message(self) -> str:
        return f"Updated {self.urls} URLs in {self.callbacks} callbacks across {self.apps} apps"


class ModifyTester:
    def __init__(self, runner: CliRunner, tmp_path: str, apps: dict[str, App], snapshot: Snapshot) -> None:
        self.runner = runner
        self.tmp_path = tmp_path
        self.apps = apps
        self.snapshot = snapshot
        self.placeholder = random_string(16)

    @contextmanager
    def isolated_filesystem(self) -> Iterator[None]:
        with self.runner.isolated_filesystem(temp_dir=self.tmp_path):
            snapshot_save("snapshot", self.snapshot)
            yield

    def gather_all(self, key: Callable[[App, Callback, CallbackURL], str]) -> list[str]:
        def gather() -> Iterator[str]:
            for app_token, callbacks in self.snapshot.items():
                app = self.apps[app_token]
                for callback in callbacks:
                    for url in callback.urls:
                        yield key(app, callback, url)

        return list(gather())

    def pick_one(self, key: Callable[[App, Callback, CallbackURL], str]) -> str:
        return random.choice(self.gather_all(key))

    def run(self, args: list[str]) -> Result:
        full_args = ["snapshot", "modify"] + args + ["--add-placeholder", self.placeholder]
        self.result = self.runner.invoke(cli, full_args)
        assert self.result.exit_code == 0
        return self.result

    def ensure_snapshot_satisfies(
        self,
        filter_predicate: Callable[[App, Callback, CallbackURL], bool],
        message: str,
    ) -> None:
        updated_snapshot = snapshot_load("snapshot")
        assert updated_snapshot != self.snapshot
        counters = Counters()
        for app_token, callbacks in updated_snapshot.items():
            app = self.apps[app_token]
            for callback in callbacks:
                for url in callback.urls:
                    if filter_predicate(app, callback, url):
                        message = f"{app_token}/{callback.unique_name}: {message} has placeholder {self.placeholder}\n{self.result.output}"
                        assert self.placeholder in url.placeholders, message
                        counters.update(app_token, callback)
        assert counters.expected_message in self.result.output


@pytest.fixture
def modify_tester(runner: CliRunner, tmp_path: str, apps: dict[str, App], snapshot: Snapshot) -> ModifyTester:
    return ModifyTester(runner, tmp_path, apps, snapshot)


def test_snapshot_modify_app_token(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: a.token)
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--having-app-token", pick])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: a.token == pick,
            f"App with token {pick}",
        )


def test_snapshot_modify_having_placeholder(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: random.choice(u.placeholders))
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--having-placeholder", pick])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: pick in u.placeholders,
            f"URL with placeholder {pick}",
        )


def test_snapshot_modify_matching_placeholder(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: random.choice(u.placeholders))
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--matching-placeholder", f"^{pick}$"])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: pick in u.placeholders,
            f"URL with placeholder matching ^{pick}$",
        )


def test_snapshot_modify_having_app_name(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: a.name)
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--having-app", pick])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: a.name == pick,
            f"App with name {pick}",
        )


def test_snapshot_modify_matching_app_name(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: a.name)
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--matching-app", f"^{pick}$"])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: re.match(f"^{pick}$", a.name) is not None,
            f"App with name matching ^{pick}$",
        )


def test_snapshot_modify_having_domain(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: u.netloc)
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--having-domain", pick])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: u.netloc == pick,
            f"URL with domain {pick}",
        )


def test_snapshot_modify_matching_domain(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: u.netloc)
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--matching-domain", f"^{pick}$"])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: u.netloc == pick,
            f"URL with domain matching ^{pick}$",
        )


def test_snapshot_modify_having_path(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: u.path)
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--having-path", pick])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: u.path == pick,
            f"URL with path {pick}",
        )


def test_snapshot_modify_matching_path(modify_tester: ModifyTester) -> None:
    pick = modify_tester.pick_one(lambda a, c, u: u.path)
    with modify_tester.isolated_filesystem():
        modify_tester.run(["--matching-path", f"^{pick}$"])
        modify_tester.ensure_snapshot_satisfies(
            lambda a, c, u: u.path == pick,
            f"URL with path matching ^{pick}$",
        )


def test_snapshot_modify_none(modify_tester: ModifyTester) -> None:
    pick = random_string(16)
    with modify_tester.isolated_filesystem():
        result = modify_tester.run(["--matching-path", pick])
        assert result.exit_code == 0
        updated_snapshot = snapshot_load("snapshot")
        assert updated_snapshot == modify_tester.snapshot
        assert "⚠️ No URLs matched the pattern." in modify_tester.result.output


def test_snapshot_modify_bad_regex(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["snapshot", "modify", "--matching-path", "("])
    assert result.exit_code == 2
    assert "Invalid regex:" in result.output
