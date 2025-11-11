"""Profiles rebuild command handler - Admin command to rebuild user profiles."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.context_extractor import message_history
from utils.profile_manager import profile_manager
from ai_providers import create_provider
from .base import Command
from .arguments import ArgumentDefinition, ArgumentType, ArgumentParseError

logger = logging.getLogger(__name__)
config = get_config()


class ProfilesRebuildCommand(Command):
    """Profiles-Rebuild command for rebuilding user profiles from message history.

    Admin command that rebuilds AI profiles using different data sources.
    Supports rebuilding for specific users, all users, or filtered by channel.
    """

    def __init__(self):
        arguments = [
            ArgumentDefinition(
                name="user",
                type=ArgumentType.STRING,
                required=True,
                description="User ID or 'all' for all known users from message history. Example: 123456789 or all"
            ),
            ArgumentDefinition(
                name="source",
                type=ArgumentType.CHOICE,
                required=False,
                choices=["context", "N", "full"],
                description="'context' (default), 'N' (last N messages), or 'full' (all history)"
            ),
            ArgumentDefinition(
                name="channel",
                type=ArgumentType.STRING,
                required=True,
                description="'current' (current channel only), 'all' (all channels bot is in), or channel ID (e.g., -123456789)"
            )
        ]
        super().__init__(
            name="profiles_rebuild",
            description="Rebuild user profiles from message history",
            admin_only=True,
            arguments=arguments
        )

    def _get_raw_help_text(self, language: str = "en") -> str:
        """Get raw help text for the profiles_rebuild command."""
        help_lines = [
            f"{self.command_name} - {self.description}",
            "",
            "USAGE:",
            "/profiles_rebuild <user>|all [context|N|full] <channel>",
            "",
            "PARAMETERS:",
            "<user>|all      : User ID (e.g., 123456789) or 'all' for all known users from message history",
            "[context|N|full]: Data source (optional, default: context)",
            "                  - context: Use current stored context messages",
            "                  - N: Use last N messages from Telegram API",
            "                  - full: Use full chat history from Telegram API",
            "<channel>       : Channel scope (required)",
            "                  - current: Use only current channel history",
            "                  - all: Use history from all channels bot is in",
            "                  - <channel_id>: Use specific channel (e.g., -123456789)",
            "",
            "EXAMPLES:",
            "/profiles_rebuild 123456789 context current    # Rebuild user using current channel context",
            "/profiles_rebuild all full all                 # Rebuild ALL KNOWN users using full history from ALL channels",
            "/profiles_rebuild all N -123456789             # Rebuild all users from specific channel using last N messages",
            "",
            "NOTE: 'all' discovers all users from message history and rebuilds their profiles. Uses batching for performance."
        ]

        return "\n".join(help_lines)

    def can_execute(self, user_id: int, config) -> bool:
        """Check if user can execute this command - admin only."""
        return user_id in config.admin_user_ids

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /profiles-rebuild command."""
        if not update.message:
            return

        message = update.message
        user_id = message.from_user.id if message.from_user else 0

        # Admin check
        if user_id not in config.admin_user_ids:
            await message.reply_text("❌ Only administrators can rebuild user profiles.")
            return

        try:
            # Parse arguments - strip command name from message text
            command_text = message.text.strip()
            args_text = command_text.replace(self.command_name, '', 1).strip()

            try:
                args = self.parse_arguments(args_text)
            except ArgumentParseError as e:
                await message.reply_text(
                    f"❌ Invalid arguments: {str(e)}\n\n"
                    f"Usage: /profiles_rebuild <user>|all [context|N|full] <channel>\n"
                    f"Example: /profiles_rebuild all full current"
                )
                return

            if not args or "user" not in args:
                await message.reply_text(
                    "❌ Invalid syntax. Use: /profiles_rebuild <user>|all [context|N|full] <channel>\n"
                    "Example: /profiles_rebuild all full current"
                )
                return

            target_user = args["user"]
            source = args.get("source", "context")
            channel_param = args["channel"]

            # Validate user target
            if target_user == "all":
                target_user_ids = None  # Will process all users with existing profiles
            else:
                try:
                    target_user_ids = [int(target_user)]
                except ValueError:
                    await message.reply_text(f"❌ Invalid user ID: {target_user}")
                    return

            # Validate channel parameter
            if channel_param == "current":
                channel_filter = message.chat_id  # Use current channel
                channel_description = "current channel"
            elif channel_param == "all":
                channel_filter = None  # Use all channels
                channel_description = "all channels"
            else:
                # Try to parse as channel ID
                try:
                    channel_filter = int(channel_param)
                    channel_description = f"channel {channel_filter}"
                except ValueError:
                    await message.reply_text(f"❌ Invalid channel parameter: {channel_param}. Use 'current', 'all', or a channel ID (e.g., -123456789).")
                    return

            # Validate source
            if source not in ["context", "N", "full"]:
                await message.reply_text(f"❌ Invalid source: {source}. Use 'context', 'N', or 'full'.")
                return

            await self._rebuild_profiles(target_user_ids, source, channel_filter, channel_param, channel_description, message)

        except Exception as e:
            logger.error(f"Error in profiles-rebuild command: {e}")
            await message.reply_text("❌ Error rebuilding user profiles.")

    async def _rebuild_profiles(self, target_user_ids, source: str, channel_filter, channel_param, channel_description, message) -> None:
        """Rebuild user profiles using the specified parameters."""
        try:
            # Get AI provider for profile enrichment
            ai_provider = create_provider(
                provider_type=config.ai_provider,
                api_key=config.api_key,
                model=config.model_name,
                base_url=config.base_url,
            )

            if target_user_ids is None:
                # Rebuild all known users (from message history)
                await message.reply_text(
                    f"🔄 Starting profile rebuild for ALL KNOWN users using {source} data from {channel_description}...\n\n"
                    "This may take several minutes depending on the number of users and data size."
                )

                # Get all user IDs from message history
                all_known_user_ids = set()

                # For "full" source, get actual channel participants via Telegram API
                # For "context" source, scan stored message history
                if source == "full":
                    # For full rebuilds, we need to get actual channel participants
                    # This requires bot instance and API calls - for now, fall back to message history scanning
                    # TODO: Implement proper Telegram API participant fetching
                    logger.info("Full rebuild requested - scanning message history for user discovery")
                    pass

                # Scan message history to find all users
                if channel_param == "current":
                    # Only scan current channel
                    chat_ids_to_scan = [message.chat_id]
                elif channel_param == "all":
                    # Scan all channels
                    chat_ids_to_scan = message_history.get_all_chat_ids()
                    logger.info(f"Found {len(chat_ids_to_scan)} chats to scan: {chat_ids_to_scan}")
                else:
                    # Scan specific channel
                    chat_ids_to_scan = [int(channel_param)]

                for chat_id in chat_ids_to_scan:
                    try:
                        # Get recent messages to find users
                        recent_messages = message_history.get_recent_messages(chat_id, limit=1000) or []
                        logger.info(f"Scanning chat {chat_id}: found {len(recent_messages)} messages")
                        if recent_messages:
                            logger.info(f"Sample message from chat {chat_id}: {recent_messages[0]}")
                        for msg in recent_messages:
                            user_id = msg.get("user_id")
                            if user_id and user_id != 0:  # Skip invalid user IDs
                                all_known_user_ids.add(user_id)
                                logger.debug(f"Found user {user_id} in chat {chat_id}")
                    except Exception as e:
                        logger.warning(f"Failed to scan chat {chat_id} for users: {e}")
                        import traceback
                        logger.warning(f"Traceback: {traceback.format_exc()}")

                target_user_ids = list(all_known_user_ids)

                if not target_user_ids:
                    await message.reply_text(f"❌ No users found in {channel_description}.")
                    return

                logger.info(f"Found {len(target_user_ids)} users to rebuild profiles for")
            else:
                # Rebuild specific user
                user_id = target_user_ids[0]
                channel_desc = f" from channel {channel_filter}" if channel_filter else ""
                await message.reply_text(
                    f"🔄 Starting profile rebuild for user {user_id} using {source} data{channel_desc}..."
                )

            # For profile rebuilding, we process each user individually
            # The source parameter determines how many messages to use per user
            if source == "full":
                source_description = "full message history"
                messages_per_user = 100  # Use up to 100 messages per user
            elif source == "N":
                source_description = "last N messages from history"
                messages_per_user = getattr(config, 'rebuild_n_messages', 50)
            else:  # context
                source_description = "current context messages"
                messages_per_user = 30  # Use recent context messages

            await message.reply_text(
                f"🔄 Processing profiles for rebuild...\n\n"
                f"📊 Data Source: {source_description}\n"
                f"👥 Target Users: {len(target_user_ids) if target_user_ids else 'all'}"
            )

            # Rebuild profiles for each user in batches
            batch_size = 3  # Process 3 users at a time (AI calls are expensive)
            total_processed = 0
            successful_rebuilds = 0
            total_messages_processed = 0

            for i in range(0, len(target_user_ids), batch_size):
                batch_user_ids = target_user_ids[i:i + batch_size]

                for user_id in batch_user_ids:
                    try:
                        # Get user's message history
                        if channel_filter:
                            # Get messages from specific channel only
                            user_messages = message_history.get_user_messages(channel_filter, user_id, messages_per_user)
                            # For single channel, estimate message count
                            user_messages_count = len(user_messages.split('\n')) if user_messages else 0
                        else:
                            # Get messages from all chats the user has participated in
                            # Since get_user_messages works per chat, we need to aggregate
                            user_chats = message_history.get_all_chat_ids()
                            all_user_messages = []
                            messages_count = 0
                            for chat_id in user_chats:
                                chat_messages = message_history.get_user_messages(chat_id, user_id, messages_per_user // len(user_chats) + 1)
                                if chat_messages:
                                    all_user_messages.append(chat_messages)
                                    # Count messages (rough estimate: split by newlines and filter empty)
                                    messages_count += len([msg for msg in chat_messages.split('\n') if msg.strip()])
                            user_messages = "\n".join(all_user_messages)
                            # Use the counted messages for this user
                            user_messages_count = messages_count

                        if user_messages and len(user_messages.strip()) > 10:  # Ensure we have meaningful content
                            # Enrich profile with AI
                            await profile_manager.enrich_profile_with_ai(
                                user_id=user_id, recent_messages=user_messages, ai_analyzer=ai_provider
                            )
                            successful_rebuilds += 1
                            total_messages_processed += user_messages_count
                            logger.info(f"Successfully rebuilt profile for user {user_id} using {user_messages_count} messages")
                        else:
                            logger.warning(f"No sufficient message history found for user {user_id}")

                        total_processed += 1

                    except Exception as e:
                        logger.warning(f"Failed to rebuild profile for user {user_id}: {e}")
                        total_processed += 1

                # Progress update for large batches
                if len(target_user_ids) > batch_size:
                    progress = (i + len(batch_user_ids)) / len(target_user_ids) * 100
                    await message.reply_text(
                        f"📊 Progress: {progress:.1f}% complete\n"
                        f"✅ {successful_rebuilds}/{total_processed} profiles rebuilt successfully"
                    )

            # Save all updated profiles
            profile_manager.save_all_profiles()

            # Final summary
            if target_user_ids is None:
                target_desc = "all users with existing profiles"
            else:
                target_desc = f"user {target_user_ids[0]}" if len(target_user_ids) == 1 else f"{len(target_user_ids)} users"

            channel_desc = f" from channel {channel_filter}" if channel_filter else ""

            await message.reply_text(
                f"✅ Profile rebuild completed!\n\n"
                f"👥 Target: {target_desc}{channel_desc}\n"
                f"📊 Data Source: {source_description}\n"
                f"✅ Successful: {successful_rebuilds}/{total_processed} profiles\n"
                f"💬 Messages Processed: {total_messages_processed}\n"
                f"💾 All profile data saved to disk"
            )

            logger.info(f"Rebuilt {successful_rebuilds}/{total_processed} profiles using {source_description}, processed {total_messages_processed} messages")

        except Exception as e:
            logger.error(f"Error rebuilding profiles: {e}")
            await message.reply_text("❌ Error rebuilding user profiles.")


# Create and register the command instance
profiles_rebuild_command = ProfilesRebuildCommand()
