import re
import click
import dotenv
import os
import shutil

from click_help_colors import HelpColorsGroup

from adjust.api.model import Callback, CallbackType, CallbackURL
from adjust.snapshot import (
    snapshot_callback_count,
    snapshot_diff,
    snapshot_fetch,
    snapshot_load,
    snapshot_restore,
    snapshot_save,
    snapshot_write_callback,
)

from ..api import AdjustAPI
from ..utils import AddCounters
from .types import CALLBACK_URL, REGEX


pass_api = click.make_pass_decorator(AdjustAPI)


@click.group(cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green", help="Adjust API CLI")
@click.pass_context
def cli(ctx: click.Context) -> None:
    dotenv.load_dotenv()
    ctx.obj = AdjustAPI()


@cli.group(help="Manage Adjust callback snapshots")
def snapshot() -> None:
    pass


@snapshot.command(help="Create a local snapshot of all Adjust callbacks")
@click.option(
    "--snapshot",
    "-s",
    "snapshot_path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True),
    default="snapshot",
    show_default=True,
    help="Snapshot path",
)
@click.option("--non-interactive", is_flag=True, help="Allow interaction with user")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing snapshot")
@pass_api
def create(
    api: AdjustAPI,
    snapshot_path: str,
    non_interactive: bool,
    force: bool,
) -> None:
    non_interactive = non_interactive or not os.isatty(0)
    if os.path.exists(snapshot_path):
        if not force:
            if non_interactive:
                raise click.ClickException(f"⛔️ Snapshot path `{snapshot_path}` already exists. Use --force to overwrite.")
            click.confirm(f"⚠️ Snapshot path `{snapshot_path}` already exists. Overwrite?", abort=True)
        shutil.rmtree(snapshot_path)
    snapshot = snapshot_fetch(api, progress_desc="⬇️  Creating Snapshot")
    snapshot_save(snapshot_path, snapshot)
    callback_count = snapshot_callback_count(snapshot)
    click.echo(f"✅ Done. Retrieved {callback_count} callbacks.")


@snapshot.command(help="Restore Adjust callbacks from local snapshot")
@click.option(
    "--snapshot",
    "-s",
    "snapshot_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    default="snapshot",
    show_default=True,
    help="Snapshot path",
)
@click.option("--dry-run", "-n", is_flag=True, help="Do not invoke the Adjust API, only simulate what would be done.")
@pass_api
def restore(api: AdjustAPI, snapshot_path: str, dry_run: bool) -> None:
    snapshot = snapshot_load(snapshot_path)
    current_snapshot = snapshot_fetch(api, progress_desc="⬇️  Fetching Current Snapshot")
    diff = snapshot_diff(current_snapshot, snapshot)
    if not dry_run:
        snapshot_restore(api, diff, progress_desc="⬆️  Restoring Snapshot")
    num_callbacks = snapshot_callback_count(diff)
    click.echo(f"✅ Done. {'Would have updated' if dry_run else 'Updated'} {num_callbacks} callbacks.")


# Triggers used currently by our games (and their frequencies) are:
#   46 install
#   43 attribution_update
#   42 sk_install
#   37 reattribution
#   32 click
#   29 impression
#   25 rejected_reattribution
#   25 rejected_install
#   23 sk_event
#    9 sk_qualifier           <-- Setting a threshold, standard triggers above this line
#    3 sk_install_direct
#    3 sk_cv_update
#    3 session
#    1 uninstall
#    1 subscription
#    1 reinstall
#    1 global
#    1 cost_update
#    1 att_consent
#    1 ad revenue
_STANDARD_TRIGGERS: list[CallbackType] = [
    "install", "attribution_update", "sk_install", "reattribution",
    "click", "impression", "rejected_reattribution", "rejected_install",
    "sk_event",
    # These callbacks are used only on a few games, therefore, we don't
    # consider them standard triggers yet
    # "sk_qualifier", "sk_install_direct", "sk_cv_update", "session",
    # "uninstall", "subscription", "reinstall", "global", "cost_update",
    # "att_consent", "ad_revenue",
]

@snapshot.command(help="Modify local snapshot")
@click.option(
    "--snapshot",
    "-s",
    "snapshot_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    default="snapshot",
    show_default=True,
    help="Snapshot path",
)
@click.option("--having-placeholder", multiple=True, metavar="PH", help="Only modify callbacks having placeholder PH")
@click.option("--having-app", multiple=True, metavar="NAME", help="Only modify apps named NAME")
@click.option("--having-app-token", multiple=True, metavar="TOKEN", help="Only modify apps with token TOKEN")
@click.option("--having-domain", multiple=True, metavar="DOMAIN", help="Only modify callbacks whose URL domain is DOMAIN")
@click.option("--having-path", multiple=True, metavar="PATH", help="Only modify callbacks whose URL is PATH")
@click.option("--matching-placeholder", multiple=True, type=REGEX, help="Only modify callbacks having placeholders matching REGEX")
@click.option("--matching-app", multiple=True, type=REGEX, help="Only modify apps whose name match REGEX")
@click.option("--matching-domain", multiple=True, type=REGEX, help="Only modify callbacks whose URL domain matches REGEX")
@click.option("--matching-path", multiple=True, type=REGEX, help="Only modify callbacks whose URL matches REGEX")
@click.option("--add-placeholder", "-a", multiple=True, metavar="PH", help="Add placeholder PH to all matching callbacks")
@click.option("--add-standard-callbacks", type=CALLBACK_URL, help="Add standard callbacks to all matching apps using base URL")
@click.option("--dry-run", "-n", is_flag=True, help="Do not update the snapshot, only simulate what would be done.")
@pass_api
def modify(
    api: AdjustAPI,
    snapshot_path: str,
    having_placeholder: list[str],
    having_app: list[str],
    having_app_token: list[str],
    having_domain: list[str],
    having_path: list[str],
    matching_placeholder: list[re.Pattern],
    matching_app: list[re.Pattern],
    matching_domain: list[re.Pattern],
    matching_path: list[re.Pattern],
    add_placeholder: list[str],
    add_standard_callbacks: CallbackURL,
    dry_run: bool,
) -> None:
    counters = AddCounters()
    snapshot = snapshot_load(snapshot_path)
    apps = {a.token: a for a in api.apps} if having_app or matching_app else {}
    for app_token, callbacks in snapshot.items():
        if having_app_token and not any(app_token == t for t in having_app_token):
            continue
        app_name = apps[app_token].name if app_token in apps else ""
        if having_app and not any(app_name == n for n in having_app):
            continue
        if matching_app and not any(regex.match(app_name) for regex in matching_app):
            continue
        if add_standard_callbacks:
            for trigger in _STANDARD_TRIGGERS:
                if not any(c.id == trigger for c in callbacks):
                    callback = Callback.empty_callback_for_trigger(trigger)
                    callbacks.append(callback)
        for callback in callbacks:
            modified = False
            for url in callback.urls:
                if having_placeholder and not any(ph in url.placeholders for ph in having_placeholder):
                    continue
                if matching_placeholder and not any(regex.match(ph) for regex in matching_placeholder for ph in url.placeholders):
                    continue
                if having_domain and not any(domain == url.netloc for domain in having_domain):
                    continue
                if matching_domain and not any(domain.match(url.netloc) for domain in matching_domain):
                    continue
                if having_path and not any(path == url.path for path in having_path):
                    continue
                if matching_path and not any(path.match(url.path) for path in matching_path):
                    continue
                for ph in add_placeholder:
                    url.add_placeholder(ph)
                    counters.urls += 1
                    modified = True
            if add_standard_callbacks and not any(u.netloc != add_standard_callbacks.netloc for u in callback.urls):
                url = add_standard_callbacks.copy()
                for placeholder in api.placeholders:
                    url.add_placeholder(f"{placeholder.category}_{placeholder.placeholder}")
                callback.urls.append(add_standard_callbacks)
                counters.urls += 1
                modified = True
            if modified:
                counters.apps_seen.add(app_token)
                counters.callbacks += 1
                if not dry_run:
                    snapshot_write_callback(snapshot_path, app_token, callback)
    if counters.urls == 0:
        click.echo("⚠️ No URLs matched the pattern.")
    else:
        label = "Would have updated" if dry_run else "Updated"
        click.echo(f"✅ Done. {label} {counters.urls} URLs in {counters.callbacks} callbacks across {counters.apps} apps.")


def main() -> None:
    cli(max_content_width=120)
