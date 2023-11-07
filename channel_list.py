import re
import sys
from pathlib import Path

# matches against a 'singly' or "doubly" quoted string
__quoted_string = re.compile(r"""^(['"])([^\1]+)\1$""")


class ParserError(Exception):
    pass


def read_channel_list(fp: str | Path) -> dict[int, str]:
    """Read from a filepath into a mapping of channel ID to channel name."""
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
        match = re.match(r"(\d+)\s+(.+)", line)
        if not match:
            raise ParserError("Couldn't get a match!", f"bad line: {line}")

        channel_id = int(match[1])

        # if channel name is not wrapped in quote blocks, then its
        # spaces should be reduced & its characters should be lowered.
        # this is primarily for categories
        quoted_line = re.match(__quoted_string, match[2])

        if quoted_line:
            resp[channel_id] = quoted_line[2]
        else:
            name = re.sub(r"\s+", "-", match[2].lower())
            resp[channel_id] = name

    return resp


def read_channel_lists(*paths: str | Path) -> dict[int, str]:
    """Read channel lists from multiple paths into one mapping."""
    if not paths:
        return {}
    resp = read_channel_list(paths[0])
    for path in paths[1:]:
        resp.update(read_channel_list(path))
    return resp
