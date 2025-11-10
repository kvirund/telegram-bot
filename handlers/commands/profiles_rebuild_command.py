"""Profiles rebuild command handler - Admin command to rebuild user profiles."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.context_extractor import message_history
from utils.profile_manager import profile_manager
from ai_providers import create_provider
from .base import Command
from .arguments import ArgumentDefinition, ArgumentType

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
                description="User ID or 'all' for all existing profiles. Example: 123456789 or all"
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
                required=False,
                description="Optional channel ID to limit data source. Example: -123456789"
            )
        ]
        super().__init__(
            name="profiles-rebuild",
            description="Rebuild user profiles from message history",
            admin_only=True,
            arguments=arguments
        )

    def get_help_text(self, language: str = "en") -> str:
        """Get help text for the profiles-rebuild command."""
        help_lines = [
            f"{self.command_name} - {self.description}",
            "",
            "USAGE:",
            "/profiles-rebuild <user>|all [context|N|full] [<channel>]",
            "",
            "PARAMETERS:",
            "<user>|all      : User ID (e.g., 123456789) or 'all' for all existing profiles",
            "[context|N|full]: Data source (optional, default: context)",
            "                  - context: Use current stored context messages",
            "                  - N: Use last N messages from Telegram API",
            "                  - full: Use full chat history from Telegram API",
            "[<channel>]     : Optional channel ID to limit data source",
            "",
            "EXAMPLES:",
            "/profiles-rebuild 123456789              # Rebuild specific user using context",
            "/profiles-rebuild all full               # Rebuild all profiles using full history",
            "/profiles-rebuild all N -123456789       # Rebuild all profiles using last N messages from specific channel",
            "/profiles-rebuild 123456789 context      # Rebuild user using context messages",
            "",
            "NOTE: 'all' rebuilds only users who already have profiles. Uses batching for performance."
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
            # Parse arguments
            args = self.parse_arguments(message.text)

            if not args or "user" not in args:
                await message.reply_text(
                    "❌ Invalid syntax. Use: /profiles-rebuild <user>|all [context|N|full] [<channel>]\n"
                    "Example: /profiles-rebuild all full -123456789"
                )
                return

            target_user = args["user"]
            source = args.get("source", "context")
            channel_filter = args.get("channel")

            # Validate user target
            if target_user == "all":
                target_user_ids = None  # Will process all users with existing profiles
            else:
                try:
                    target_user_ids = [int(target_user)]
                except ValueError:
                    await message.reply_text(f"❌ Invalid user ID: {target_user}")
                    return

            # Validate channel filter if provided
            if channel_filter:
                try:
                    channel_filter = int(channel_filter)
                except ValueError:
                    await message.reply_text(f"❌ Invalid channel ID: {channel_filter}")
                    return

            # Validate source
            if source not in ["context", "N", "full"]:
                await message.reply_text(f"❌ Invalid source: {source}. Use 'context', 'N', or 'full'.")
                return

            await self._rebuild_profiles(target_user_ids, source, channel_filter, message)

        except Exception as e:
            logger.error(f"Error in profiles-rebuild command: {e}")
            await message.reply_text("❌ Error rebuilding user profiles.")

    async def _rebuild_profiles(self, target_user_ids, source: str, channel_filter, message) -> None:
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
                # Rebuild all existing profiles
                await message.reply_text(
                    f"🔄 Starting profile rebuild for ALL users using {source} data...\n\n"
                    "This may take several minutes depending on the number of users and data size."
                )

                # Get all user IDs that have existing profiles
                import os
                users_dir = os.path.join(profile_manager.profile_directory, "users")
                all_user_ids = []
                if os.path.exists(users_dir):
                    for filename in os.listdir(users_dir):
                        if filename.startswith("user_") and filename.endswith(".json"):
                            try:
                                user_id_str = filename.replace("user_", "").replace(".json", "")
                                all_user_ids.append(int(user_id_str))
                            except ValueError:
                                continue
                target_user_ids = all_user_ids

                if not target_user_ids:
                    await message.reply_text("❌ No users found with existing profiles.")
                    return
            else:
                # Rebuild specific user
                user_id = target_user_ids[0]
                channel_desc = f" from channel {channel_filter}" if channel_filter else ""
                await message.reply_text(
                    f"🔄 Starting profile rebuild for user {user_id} using {source} data{channel_desc}..."
                )

            # Determine message source based on rebuild_mode
            if source == "full":
                source_description = "full chat history"
                if channel_filter:
                    all_messages = message_history.get_all_messages_for_chat(channel_filter) or []
                else:
                    # For full rebuild without channel filter, we'd need to aggregate from all chats
                    # This is complex, so for now we'll use context as fallback
                    all_messages = []
                    for user_id in target_user_ids:
                        user_messages = message_history.get_recent_messages_for_user(user_id) or []
                        all_messages.extend(user_messages)
                    source_description = "available message history (channel filter not supported for 'full' mode)"
            elif source == "N":
                source_description = "last N messages from history"
                # Use N messages from history (configurable, defaulting to 100)
                n_messages = getattr(config, 'rebuild_n_messages', 100)
                if channel_filter:
                    all_messages = message_history.get_recent_messages(channel_filter, limit=n_messages) or []
                else:
                    all_messages = []
                    for user_id in target_user_ids:
                        user_messages = message_history.get_recent_messages_for_user(user_id, limit=n_messages) or []
                        all_messages.extend(user_messages)
            else:  # context
                source_description = "current context messages"
                all_messages = []
                for user_id in target_user_ids:
                    user_messages = message_history.get_recent_messages_for_user(user_id) or []
                    all_messages.extend(user_messages)

            if not all_messages:
                await message.reply_text(f"❌ No {source_description} available for the specified users.")
                return

            await message.reply_text(
                f"🔄 Processing {len(all_messages)} messages for profile rebuild...\n\n"
                f"📊 Data Source: {source_description}\n"
                f"👥 Target Users: {len(target_user_ids)}"
            )

            # Group messages by user
            messages_by_user = {}
            for msg in all_messages:
                user_id = msg.get("from", {}).get("id")
                if user_id and (not target_user_ids or user_id in target_user_ids):
                    if user_id not in messages_by_user:
                        messages_by_user[user_id] = []
                    messages_by_user[user_id].append(msg)

            # Rebuild profiles for each user in batches
            batch_size = 5  # Process 5 users at a time
            total_processed = 0
            successful_rebuilds = 0

            user_ids_list = list(messages_by_user.keys())

            for i in range(0, len(user_ids_list), batch_size):
                batch_user_ids = user_ids_list[i:i + batch_size]

                for user_id in batch_user_ids:
                    try:
                        user_messages = messages_by_user[user_id]

                        # Convert messages to text for AI analysis
                        message_texts = []
                        for msg in user_messages[-50:]:  # Limit to last 50 messages per user for AI processing
                            if "text" in msg and msg["text"]:
                                sender_name = msg.get("from", {}).get("first_name", "User")
                                message_texts.append(f"{sender_name}: {msg['text']}")

                        if message_texts:
                            message_history_text = "\n".join(message_texts)

                            # Enrich profile with AI
                            await profile_manager.enrich_profile_with_ai(
                                user_id=user_id, recent_messages=message_history_text, ai_analyzer=ai_provider
                            )

                            successful_rebuilds += 1

                        total_processed += 1

                    except Exception as e:
                        logger.warning(f"Failed to rebuild profile for user {user_id}: {e}")
                        total_processed += 1

                # Progress update for large batches
                if len(user_ids_list) > batch_size:
                    progress = (i + len(batch_user_ids)) / len(user_ids_list) * 100
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
                f"💾 All profile data saved to disk"
            )

            logger.info(f"Rebuilt {successful_rebuilds}/{total_processed} profiles using {source_description}")

        except Exception as e:
            logger.error(f"Error rebuilding profiles: {e}")
            await message.reply_text("❌ Error rebuilding user profiles.")


# Create and register the command instance
profiles_rebuild_command = ProfilesRebuildCommand()
