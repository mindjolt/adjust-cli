import click
import re

from typing import Optional

from adjust.api.model import CallbackURL


class RegexType(click.ParamType):
    name = "regex"

    def convert(self, arg: str, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> re.Pattern:
        try:
            return re.compile(arg, re.IGNORECASE)
        except Exception as e:
            self.fail(f"Invalid regex: {e}", param, ctx)

    def get_metavar(self, param: click.Parameter) -> str | None:
        return "REGEX"


REGEX = RegexType()


class CallbackURLType(click.ParamType):
    name = "callback-url"

    def convert(self, arg: str, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> CallbackURL:
        try:
            return CallbackURL.from_url(arg)
        except Exception as e:
            self.fail(f"Invalid callback URL: {e}", param, ctx)

    def get_metavar(self, param: click.Parameter) -> str | None:
        return "URL"


CALLBACK_URL = CallbackURLType()
