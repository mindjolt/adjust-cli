from requests_mock import Mocker
import yaml
from adjust.api.api import AdjustAPI
from adjust.api.model import Callback
from adjust.snapshot import Snapshot, snapshot_fetch, snapshot_load, snapshot_restore, snapshot_save


def test_snapshot_fetch(api: AdjustAPI, snapshot: Snapshot) -> None:
    assert snapshot_fetch(api) == snapshot


def test_snapshot_restore(requests_mock: Mocker, api: AdjustAPI, snapshot: Snapshot) -> None:
    for app_token, callbacks in snapshot.items():
        for callback in callbacks:
            requests_mock.put(
                f"https://api.adjust.com/dashboard/api/apps/{app_token}/event_types/{callback.id}/callback",
                status_code=204,
            )
    snapshot_restore(api, snapshot)
    requests = {r.path: r for r in requests_mock.request_history if r.method == "PUT"}
    for app_token, callbacks in snapshot.items():
        for callback in callbacks:
            request = requests[f"/dashboard/api/apps/{app_token}/event_types/{callback.id}/callback"]
            assert request.json() == dict(callback_url=callback.url)


def test_snapshot_save(snapshot: Snapshot, tmp_path: str) -> None:
    snapshot_save(tmp_path, snapshot)
    for app_token, callbacks in snapshot.items():
        for callback in callbacks:
            with open(f"{tmp_path}/{app_token}/{callback.unique_name}.yaml") as file:
                data = yaml.safe_load(file)
                assert Callback.parse_obj(data) == callback


def test_snapshot_load(snapshot: Snapshot, tmp_path: str) -> None:
    snapshot_save(tmp_path, snapshot)
    loaded = snapshot_load(tmp_path)
    assert loaded == snapshot
