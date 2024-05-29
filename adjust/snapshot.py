import os
from typing import Optional
import yaml

from .utils import progress_bar

from .api.api import AdjustAPI
from .api.model import Callback

Snapshot = dict[str, list[Callback]]


def snapshot_save(path: str, snapshot: Snapshot) -> None:
    """
    Save the snapshot data to YAML files.

    Args:
        path (str): The directory path where the snapshot files will be saved.
        snapshot (Snapshot): The snapshot data to be saved.

    Returns:
        None
    """
    for app_token, callbacks in snapshot.items():
        for callback in callbacks:
            snapshot_write_callback(path, app_token, callback)


def snapshot_write_callback(path: str, app_token: str, callback: Callback) -> None:
    """
    Write a single callback to a YAML file.

    Args:
        path (str): The snapshot path
        app_token (str): The token of the app owning the callback.
        callback (Callback): The callback object containing the data to be written.

    Returns:
        None
    """
    if callback.urls:
        app_path = os.path.join(path, app_token)
        os.makedirs(app_path, exist_ok=True)
        filename = os.path.join(app_path, f"{callback.unique_name}.yaml")
        with open(filename, "w") as file:
            yaml.dump(callback.dict(), file, sort_keys=False)


def snapshot_load(path: str) -> Snapshot:
    """
    Load a snapshot from the given path.

    Args:
        path (str): The path to the directory containing the snapshot files.

    Returns:
        Snapshot: The loaded snapshot as a dictionary.

    """
    snapshot: Snapshot = {}
    for app_token in os.listdir(path):
        app_path = os.path.join(path, app_token)
        if os.path.isdir(app_path):
            for filename in os.listdir(app_path):
                file_path = os.path.join(app_path, filename)
                if os.path.isfile(file_path):
                    with open(file_path) as file:
                        data = yaml.safe_load(file)
                        callback = Callback.parse_obj(data)
                        snapshot.setdefault(app_token, []).append(callback)
    return normalize_snapshot(snapshot)


def snapshot_fetch(api: AdjustAPI, progress_desc: Optional[str] = None) -> Snapshot:
    """
    Fetches a snapshot of all callbacks from all apps using the Adjust API.

    Args:
        api (AdjustAPI): An instance of the AdjustAPI class.
        progress_desc (Optional[str]): A description for the progress bar (default: None).

    Returns:
        Snapshot: The fetched snapshot as a dictionary.
    """
    snapshot: Snapshot = {}
    for app in progress_bar(sorted(api.apps, key=lambda app: app.token), desc=progress_desc):
        snapshot[app.token] = api.callbacks(app)
    return normalize_snapshot(snapshot)


def snapshot_restore(api: AdjustAPI, snapshot: Snapshot, progress_desc: Optional[str] = None) -> None:
    """
    Restores the callbacks snapshot by updating them using the Adjust API.

    Args:
        api (AdjustAPI): An instance of the AdjustAPI class used to update the callbacks.
        snapshot (Snapshot): The snapshot to restore.
        progress_desc (Optional[str]): A description for the progress bar (default: None).

    Returns:
        None
    """
    ops = [(app_token, callback) for app_token, callbacks in snapshot.items() for callback in callbacks]
    for app_token, callback in progress_bar(ops, progress_desc):
        api.update_callback(app_token, callback)


def snapshot_diff(snapshot1: Snapshot, snapshot2: Snapshot) -> Snapshot:
    """
    Compares two snapshots and returns the difference between them.

    Args:
        snapshot1 (Snapshot): The first snapshot to compare.
        snapshot2 (Snapshot): The second snapshot to compare.

    Returns:
        Snapshot: A dictionary representing the difference between the two snapshots.
                 The keys of the dictionary are the app tokens, and the values are lists
                 of callbacks that are present in snapshot2 but not in snapshot1.
    """
    diff: Snapshot = {}
    for app_token in snapshot1.keys() | snapshot2.keys():
        callbacks1 = snapshot1.get(app_token, [])
        callbacks2 = snapshot2.get(app_token, [])
        diff[app_token] = [callback for callback in callbacks2 if callback not in callbacks1]
    return normalize_snapshot(diff)


def snapshot_callback_count(snapshot: Snapshot) -> int:
    """
    Calculates the total number of callbacks in the given snapshot.

    Args:
        snapshot (Snapshot): The snapshot containing the callbacks.

    Returns:
        int: The total number of callbacks in the snapshot.
    """
    return sum(len(callbacks) for callbacks in snapshot.values())


def normalize_snapshot(snapshot: Snapshot) -> Snapshot:
    return {app_token: sorted(callbacks, key=lambda c: c.unique_name) for app_token, callbacks in snapshot.items() if callbacks}
