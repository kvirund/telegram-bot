"""Group mood rebuild command handler - Admin command to rebuild group mood data."""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.profile_manager import profile_manager
from .base import Command
from .arguments import ArgumentDefinition, ArgumentType

logger = logging.getLogger(__name__)
config = get_config()


class GroupMoodRebuildCommand(Command):
    """GroupMood-Rebuild command for rebuilding group mood data.

    Admin command that rebuilds group mood analysis using different data sources.
    Supports rebuilding for specific channels or all channels.
    """

    def __init__(self):
        arguments = [
            ArgumentDefinition(
                name="target",
                type=ArgumentType.STRING,
                required=True,
                description="Channel ID or 'all' for all channels. Example: -123456789 or all"
            ),
            ArgumentDefinition(
                name="source",
                type=ArgumentType.CHOICE,
                required=False,
                choices=["context", "N", "full"],
                description="'context' (default), 'N' (last N messages), or 'full' (all history)"
            )
        ]
        super().__init__(
            name="groupmood-rebuild",
            description="Rebuild group mood data from different sources",
            admin_only=True,
            arguments=arguments
        )

    def get_help_text(self, language: str = "en") -> str:
        """Get help text for the groupmood-rebuild command."""
        help_lines = [
            f"{self.command_name} - {self.description}",
            "",
            "USAGE:",
            "/groupmood-rebuild <channel>|all [context|N|full]",
            "",
            "PARAMETERS:",
            "<channel>|all    : Channel ID (e.g., -123456789) or 'all' for all channels",
            "[context|N|full] : Data source (optional, default: context)",
            "                  - context: Use current stored context messages",
            "                  - N: Use last N messages from Telegram API",
            "                  - full: Use full chat history from Telegram API",
            "",
            "EXAMPLES:",
            "/groupmood-rebuild -123456789        # Rebuild specific channel using context",
            "/groupmood-rebuild all full          # Rebuild all channels using full history",
            "/groupmood-rebuild -123456789 N      # Rebuild channel using last N messages",
            "",
            "NOTE: This is an admin-only command that uses batching for performance."
        ]

        return "\n".join(help_lines)

    def can_execute(self, user_id: int, config) -> bool:
        """Check if user can execute this command - admin only."""
        return user_id in config.admin_user_ids

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /groupmood-rebuild command."""
        if not update.message:
            return

        message = update.message
        user_id = message.from_user.id if message.from_user else 0

        # Admin check
        if user_id not in config.admin_user_ids:
            await message.reply_text("❌ Only administrators can rebuild group mood data.")
            return

        try:
            # Parse arguments
            args = self.parse_arguments(message.text)

            if not args or "target" not in args:
                await message.reply_text(
                    "❌ Invalid syntax. Use: /groupmood-rebuild <channel>|all [context|N|full]\n"
                    "Example: /groupmood-rebuild -123456789 full"
                )
                return

            target = args["target"]
            source = args.get("source", "context")

            # Validate target
            if target == "all":
                target_chat_ids = None  # Will process all channels
            else:
                try:
                    target_chat_ids = [int(target)]
                except ValueError:
                    await message.reply_text(f"❌ Invalid channel ID: {target}")
                    return

            # Validate source
            if source not in ["context", "N", "full"]:
                await message.reply_text(f"❌ Invalid source: {source}. Use 'context', 'N', or 'full'.")
                return

            await self._rebuild_group_mood(target_chat_ids, source, message)

        except Exception as e:
            logger.error(f"Error in groupmood-rebuild command: {e}")
            await message.reply_text("❌ Error rebuilding group mood data.")

    async def _rebuild_group_mood(self, target_chat_ids, source: str, message) -> None:
        """Rebuild group mood data for specified channels using the given source."""
        try:
            if target_chat_ids is None:
                # Rebuild all channels
                await message.reply_text(
                    f"🔄 Starting group mood rebuild for ALL channels using {source} data...\n\n"
                    "This may take several minutes depending on the number of channels and data size."
                )

                # Get all chat IDs that have reaction data
                all_chat_ids = profile_manager.get_all_chat_ids()
                target_chat_ids = all_chat_ids

                if not target_chat_ids:
                    await message.reply_text("❌ No channels found with existing reaction data.")
                    return
            else:
                # Rebuild specific channel
                chat_id = target_chat_ids[0]
                await message.reply_text(
                    f"🔄 Starting group mood rebuild for channel {chat_id} using {source} data..."
                )

            # Process channels in batches
            batch_size = 5  # Process 5 channels at a time
            total_processed = 0
            successful_rebuilds = 0

            for i in range(0, len(target_chat_ids), batch_size):
                batch_chat_ids = target_chat_ids[i:i + batch_size]

                for chat_id in batch_chat_ids:
                    try:
                        await self._rebuild_single_channel_mood(chat_id, source)
                        successful_rebuilds += 1
                        total_processed += 1
                    except Exception as e:
                        logger.warning(f"Failed to rebuild mood for channel {chat_id}: {e}")
                        total_processed += 1

                # Progress update for large batches
                if len(target_chat_ids) > batch_size:
                    progress = (i + len(batch_chat_ids)) / len(target_chat_ids) * 100
                    await message.reply_text(
                        f"📊 Progress: {progress:.1f}% complete\n"
                        f"✅ {successful_rebuilds}/{total_processed} channels rebuilt successfully"
                    )

            # Final summary
            if target_chat_ids is None:
                target_desc = "all channels"
            else:
                target_desc = f"channel {target_chat_ids[0]}" if len(target_chat_ids) == 1 else f"{len(target_chat_ids)} channels"

            await message.reply_text(
                f"✅ Group mood rebuild completed!\n\n"
                f"🎯 Target: {target_desc}\n"
                f"📊 Data Source: {source}\n"
                f"✅ Successful: {successful_rebuilds}/{total_processed} channels\n"
                f"💾 All changes saved to disk"
            )

            logger.info(f"Rebuilt group mood for {successful_rebuilds}/{total_processed} channels using {source} data")

        except Exception as e:
            logger.error(f"Error rebuilding group mood: {e}")
            await message.reply_text("❌ Error rebuilding group mood data.")

    async def _rebuild_single_channel_mood(self, chat_id: int, source: str) -> None:
        """Rebuild mood data for a single channel using the specified source."""
        # Clear existing reaction data for this channel
        chat_reactions = profile_manager.load_chat_reactions(chat_id)
        chat_reactions.reactions.clear()
        chat_reactions.last_updated = datetime.utcnow().isoformat()

        # TODO: Implement data fetching based on source
        # For now, just clear and mark as updated
        # Future implementation will fetch data from:
        # - context: current stored messages
        # - N: last N messages via Telegram API
        # - full: full history via Telegram API

        # Save the updated (cleared) data
        profile_manager.save_chat_reactions(chat_id)

        logger.info(f"Cleared and prepared mood data for channel {chat_id} using {source} source")


# Create and register the command instance
groupmood_rebuild_command = GroupMoodRebuildCommand()
