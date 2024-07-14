#!/usr/bin/env python3

import asyncio
import logging
from typing import TYPE_CHECKING, override

import discord
from discord import Client, Intents
from tap import Tap

from auth import login_with_env
from theme import Theme, read_themes


class Args(Tap):
    themes: list[str]
    """The list(s) you plan on using. Supports '-' for reading from stdin."""
    guild: int = 271034455462772737
    """ID of server for which to update channel names. Defaults to Cansti's."""
    dry_run: bool = False
    """Dry-run mode."""
    reason: str | None = None
    """Reason supplied to audit log for channel update."""
    debug: bool = False
    """Emit debug-level logs."""

    @override
    def configure(self) -> None:
        self.add_argument("themes", nargs="+")
        self.add_argument("-n", "--dry-run")


async def rename_channels(
    client: discord.Client,
    cansti: discord.Guild,
    theme: Theme,
    *,
    dry_run: bool,
    reason: str | None = None,
) -> None:
    me = cansti.get_member(getattr(client.user, "id", -1))

    if me is None:
        raise RuntimeError("Couldn't get client relative to guild.")

    channel_theme_updates: list[tuple[str, str]] = []

    for channel_id, target_name in theme.items():
        channel = cansti.get_channel_or_thread(channel_id)
        log: tuple[int, str | None] = (0, None)

        if channel is None:
            log = (logging.ERROR, f"Couldn't find channel")
        elif channel.name == target_name:
            log = (logging.DEBUG, f"Channel would be updated to same name")
        elif channel.permissions_for(me).manage_channels is False:
            log = (logging.ERROR, f"Lacking 'Manage Channel' permissions for channel")

        if log[1] is not None:
            logging.log(log[0], f"{log[1]}: {channel_id:<19} {target_name}")
            continue

        if TYPE_CHECKING:
            assert channel is not None

        update = (channel.name, target_name)

        try:
            if not dry_run:
                await channel.edit(name=target_name, reason=reason)
            channel_theme_updates.append(update)
        except Exception:
            logging.exception(f"Couldn't update channel with id {channel_id}")

    if len(channel_theme_updates) == 0:
        return

    max_old_len = max(len(c[0]) for c in channel_theme_updates)

    for old, new in channel_theme_updates:
        old = old.ljust(max_old_len)
        logging.info(f"Updated channel:  {old} │ {new}")


async def main() -> None:
    args = Args(underscores_to_dashes=True).parse_args()

    # Discord has a lot of output we don't care about,
    # but it does have a nice color logger handler.
    # I used their handler for root level logging and disabled their output.

    discord.utils.setup_logging(level=10 if args.debug else 20)
    logging.getLogger("discord").propagate = False

    theme = read_themes(*args.themes)

    async with Client(intents=Intents.default()) as client:
        await login_with_env(client)
        logging.info("Logged in!")
        await client.wait_until_ready()
        logging.info("Ready to start!")

        cansti = client.get_guild(args.guild)
        if cansti is None:
            raise RuntimeError("couldn't find the guild!")

        await rename_channels(
            client, cansti, theme, dry_run=args.dry_run, reason=args.reason
        )


if __name__ == "__main__":
    asyncio.run(main())
