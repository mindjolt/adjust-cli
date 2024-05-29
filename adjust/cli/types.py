import click
import re

from typing import Optional


class RegexType(click.ParamType):
    name = "regex"

    def convert(self, arg: str, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> re.Pattern:
        try:
            return re.compile(arg)
        except Exception as e:
            self.fail(f"Invalid regex: {e}", param, ctx)

    def get_metavar(self, param: click.Parameter) -> str | None:
        return "REGEX"


REGEX = RegexType()
