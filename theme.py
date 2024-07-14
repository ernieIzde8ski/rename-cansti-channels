import re
import sys
from pathlib import Path

# matches against a 'singly' or "doubly" quoted string
__quoted_string = re.compile(r"""^(['"])([^\1]+)\1$""")


class ParserError(Exception):
    pass


type Theme = dict[int, str]
"""A mapping of Discord channel ID to channel name."""

_unlimited_spaces = re.compile(r"\s+")


def normalize_unquoted_target_name(target_name: str, /) -> str:
    return re.sub(_unlimited_spaces, "-", target_name.lower())


def read_theme(fp: str | Path) -> Theme:
    """Read from a filepath into Theme."""
    if fp == "-":
        lines = sys.stdin.readlines()
    else:
        with open(fp, "r") as file:
            lines = file.readlines()

    resp = {}

    for line in lines:
        # comments are pound signs
        comment = line.find("#")
        if comment != -1:
            line = line[:comment]

        line = line.strip()
        if not line:
            continue

        # lines take a format: channel ID, channel name
        id_name_pair = re.match(r"(\d+)\s+(.+)", line)

        if not id_name_pair:
            raise ParserError("Couldn't get a match!\n" f"bad line: {line}")

        channel_id = int(id_name_pair[1])

        # if channel name is not wrapped in quote blocks, then its
        # spaces should be reduced & its characters should be lowered.
        # this is primarily for categories
        quoted_line = re.match(__quoted_string, id_name_pair[2])

        if quoted_line:
            resp[channel_id] = quoted_line[2]
        else:
            name = normalize_unquoted_target_name(id_name_pair[2])
            resp[channel_id] = name

    return resp


def read_themes(*paths: str | Path) -> dict[int, str]:
    """Read themes from multiple paths into one mapping."""
    resp = {}

    for path in paths:
        resp.update(read_theme(path))

    return resp
