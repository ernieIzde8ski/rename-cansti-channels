#!/usr/bin/env python3

import asyncio
import logging
from typing import TYPE_CHECKING, override

import discord
from discord import Client, Intents
from tap import Tap

from auth import login_with_env
from theme import Theme, normalize_unquoted_target_name, read_themes


class Args(Tap):
    themes: list[str]
    """The list(s) you plan on using. Supports '-' for reading from stdin."""
    guild: int = 271034455462772737
    """ID of guild for which to update channel names. Defaults to Cansti's."""
    dry_run: bool = False
    """Dry-run mode."""
    reason: str | None = None
    """Reason supplied to audit log for channel update."""
    debug: bool = False
    """Emit debug-level logs."""
    emit_theme: bool = False
    """Emit the current state of the target guild as a theme, relative to the input themes. Implies --dry-run."""

    @override
    def configure(self) -> None:
        self.add_argument("themes", nargs="+")
        self.add_argument("-n", "--dry-run")

    @override
    def process_args(self) -> None:
        if self.emit_theme:
            self.dry_run = True


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


def emit_theme(cansti: discord.Guild, theme: Theme):
    for i, (channel_id, target_name) in enumerate(theme.items()):
        channel = cansti.get_channel(channel_id)

        if channel is None:
            warning_msg = "couldn't find channel with id " + str(channel_id)
            print("# WARNING:", warning_msg)
            logging.warning(warning_msg)
            continue
        elif channel.name == target_name:
            continue

        if isinstance(channel, discord.CategoryChannel) and i != 0:
            # adding an extra space before guild channels
            print()

        normalized_name = normalize_unquoted_target_name(channel.name)

        if channel.name == normalized_name:
            print(channel.id, channel.name)
        else:
            print(channel.id, f'"{channel.name}"')


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

        if args.emit_theme:
            emit_theme(cansti, theme)
        else:
            await rename_channels(
                client, cansti, theme, dry_run=args.dry_run, reason=args.reason
            )


if __name__ == "__main__":
    asyncio.run(main())
