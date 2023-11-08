import asyncio
import logging

import discord
from discord import Client, Intents
from tap import Tap

from auth import login_with_env
from channel_list import read_channel_lists


class Args(Tap):
    channel_lists: list[str]
    """The list(s) you plan on using. Supports '-' for reading from stdin."""
    guild: int = 271034455462772737
    """ID of server for which to update channel names. Defaults to Cansti's."""
    dry_run: bool = False
    """Dry-run mode."""
    reason: str | None = None
    """Reason supplied to audit log for channel update."""
    debug: bool = False
    """Emit debug-level logs."""

    def configure(self) -> None:
        self.add_argument("channel_lists", nargs="+")
        self.add_argument("-n", "--dry-run")


async def main() -> None:
    args = Args(underscores_to_dashes=True).parse_args()

    # Discord has a lot of output we don't care about,
    # but it does have a nice color logger handler.
    # I used their handler for root level logging and disabled their output.
    discord.utils.setup_logging(level=10 if args.debug else 20)
    logging.getLogger("discord").propagate = False

    channels = read_channel_lists(*args.channel_lists)

    async with Client(intents=Intents.default()) as client:
        await login_with_env(client)
        logging.info("Logged in!")
        await client.wait_until_ready()
        logging.info("Ready to start!")

        cansti = client.get_guild(args.guild)
        if cansti is None:
            raise RuntimeError("couldn't find the guild!")

        channel_updates: list[tuple[str, str]] = []
        for channel_id, name in channels.items():
            channel = cansti.get_channel_or_thread(channel_id)
            if channel is None:
                logging.error(f"Couldn't find channel: {channel_id} {name}")
            elif channel.name == name:
                logging.debug(
                    f"Channel would be updated to same name: {channel_id} {name}"
                )
            else:
                update = (channel.name, name)
                try:
                    if not args.dry_run:
                        await channel.edit(name=name, reason=args.reason)
                    channel_updates.append(update)
                except Exception:
                    logging.exception(f"Couldn't update channel with id {channel_id}")

        max_old_len = max(len(c[0]) for c in channel_updates)
        for old, new in channel_updates:
            old = old.ljust(max_old_len)
            logging.info(f"Updated channel:  {old} │ {new}")


if __name__ == "__main__":
    asyncio.run(main())
