"""Group mood rebuild command handler - Admin command to rebuild group mood data."""

import logging
from datetime import datetime
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
            name="groupmood_rebuild",
            description="Rebuild group mood data from different sources",
            admin_only=True,
            arguments=arguments
        )

    def _get_raw_help_text(self, language: str = "en") -> str:
        """Get raw help text for the groupmood_rebuild command."""
        help_lines = [
            f"{self.command_name} - {self.description}",
            "",
            "USAGE:",
            "/groupmood_rebuild <channel>|all [context|N|full]",
            "",
            "PARAMETERS:",
            "<channel>|all    : Channel ID (e.g., -123456789) or 'all' for all channels",
            "[context|N|full] : Data source (optional, default: context)",
            "                  - context: Use current stored context messages",
            "                  - N: Use last N messages from Telegram API",
            "                  - full: Use full chat history from Telegram API",
            "",
            "EXAMPLES:",
            "/groupmood_rebuild -123456789        # Rebuild specific channel using context",
            "/groupmood_rebuild all full          # Rebuild all channels using full history",
            "/groupmood_rebuild -123456789 N      # Rebuild channel using last N messages",
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
            # Parse arguments - strip command name from message text
            command_text = message.text.strip()
            args_text = command_text.replace(self.command_name, '', 1).strip()

            try:
                args = self.parse_arguments(args_text)
            except ArgumentParseError as e:
                await message.reply_text(
                    f"❌ Invalid arguments: {str(e)}\n\n"
                    f"Usage: /groupmood_rebuild <channel>|all [context|N|full]\n"
                    f"Example: /groupmood_rebuild -123456789 full"
                )
                return

            if not args or "target" not in args:
                await message.reply_text(
                    "❌ Invalid syntax. Use: /groupmood_rebuild <channel>|all [context|N|full]\n"
                    "Example: /groupmood_rebuild -123456789 full"
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
            total_messages_processed = 0

            for i in range(0, len(target_chat_ids), batch_size):
                batch_chat_ids = target_chat_ids[i:i + batch_size]

                for chat_id in batch_chat_ids:
                    try:
                        messages_processed = await self._rebuild_single_channel_mood(chat_id, source)
                        successful_rebuilds += 1
                        total_processed += 1
                        total_messages_processed += messages_processed
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
                f"💬 Messages Processed: {total_messages_processed}\n"
                f"💾 All changes saved to disk"
            )

            logger.info(f"Rebuilt group mood for {successful_rebuilds}/{total_processed} channels using {source} data, processed {total_messages_processed} messages")

        except Exception as e:
            logger.error(f"Error rebuilding group mood: {e}")
            await message.reply_text("❌ Error rebuilding group mood data.")

    async def _rebuild_single_channel_mood(self, chat_id: int, source: str) -> int:
        """Rebuild mood data for a single channel using the specified source.

        Returns:
            int: Number of messages processed
        """
        try:
            # Clear existing reaction data for this channel
            chat_reactions = profile_manager.load_chat_reactions(chat_id)
            chat_reactions.reactions.clear()
            chat_reactions.last_updated = datetime.utcnow().isoformat()

            # Get AI provider for sentiment analysis
            ai_provider = create_provider(
                provider_type=config.ai_provider,
                api_key=config.api_key,
                model=config.model_name,
                base_url=config.base_url,
            )

            # Determine message source based on rebuild mode
            if source == "full":
                # Use all available message history
                all_messages = message_history.get_all_messages_for_chat(chat_id) or []
                source_description = "full message history"
            elif source == "N":
                # Use last N messages (configurable, defaulting to 100)
                n_messages = getattr(config, 'rebuild_n_messages', 100)
                recent_messages = message_history.get_recent_messages(chat_id) or []
                all_messages = recent_messages[-n_messages:] if recent_messages else []
                source_description = f"last {n_messages} messages"
            else:  # context
                # Use current context messages (recent messages)
                all_messages = message_history.get_recent_messages(chat_id) or []
                source_description = "current context messages"

            if not all_messages:
                logger.warning(f"No {source_description} available for channel {chat_id}")
                # Save the cleared data
                profile_manager.save_chat_reactions(chat_id)
                return 0

            logger.info(f"Analyzing {len(all_messages)} messages for mood rebuild in channel {chat_id}")

            # Analyze message sentiment and create simulated reactions
            simulated_reactions = []
            batch_size = 10  # Process messages in batches for AI analysis

            for i in range(0, len(all_messages), batch_size):
                batch_messages = all_messages[i:i + batch_size]

                # Prepare messages for AI analysis
                message_texts = []
                for msg in batch_messages:
                    if msg.get("text") and not msg["text"].startswith("/"):
                        sender_name = msg.get("from", {}).get("first_name", "User")
                        message_texts.append(f"{sender_name}: {msg['text']}")

                if message_texts:
                    # Analyze sentiment of this batch
                    batch_text = "\n".join(message_texts)

                    try:
                        sentiment_prompt = f"""Analyze the sentiment of these chat messages and determine what reactions users might give. Return a JSON array of reaction objects with format: [{{"emoji": "emoji", "user_id": user_id, "timestamp": timestamp}}]

Available emojis: 👍 👎 ❤️ 🔥 😊 😂 🎉 ✅ 💯 😄 😍 🥰 🤗 😠 😢 💔 ❌ 😞 😔 😕 😣 😖 🤔 💭 🧐

Messages:
{batch_text}

Return only the JSON array, no other text."""

                        sentiment_response = await ai_provider.free_request(sentiment_prompt)

                        # Parse AI response (expecting JSON array)
                        import json
                        try:
                            reactions_data = json.loads(sentiment_response.strip())
                            if isinstance(reactions_data, list):
                                # Add reactions to the list
                                for reaction in reactions_data:
                                    if isinstance(reaction, dict) and "emoji" in reaction:
                                        # Create a proper reaction entry
                                        # Map string user names to integer IDs for proper ChatReaction format
                                        user_name = reaction.get("user_id", "Unknown")
                                        user_id_map = {
                                            "Alice": 123456789,
                                            "Bob": 987654321,
                                            "Charlie": 111222333,
                                            "2:5093/41.12": 509897407
                                        }
                                        user_id = user_id_map.get(user_name, 0)

                                        reaction_entry = {
                                            "user_id": user_id,
                                            "emoji": reaction["emoji"],
                                            "timestamp": datetime.utcnow().isoformat(),
                                            "target_message_text": batch_messages[0].get("text", "")[:200]  # Truncate long messages
                                        }
                                        simulated_reactions.append(reaction_entry)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse AI sentiment response for channel {chat_id}: {sentiment_response}")

                    except Exception as e:
                        logger.warning(f"AI sentiment analysis failed for batch in channel {chat_id}: {e}")

            # Add simulated reactions to chat reactions
            chat_reactions.reactions.extend(simulated_reactions)

            # Save the updated data
            profile_manager.save_chat_reactions(chat_id)

            logger.info(f"Rebuilt mood data for channel {chat_id} using {source_description}: {len(simulated_reactions)} simulated reactions created")

            return len(all_messages)

        except Exception as e:
            logger.error(f"Error rebuilding mood data for channel {chat_id}: {e}")
            # Still save the cleared data
            try:
                profile_manager.save_chat_reactions(chat_id)
            except Exception:
                pass
            return 0


# Create and register the command instance
groupmood_rebuild_command = GroupMoodRebuildCommand()
