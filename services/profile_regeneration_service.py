"""Service for regenerating user profiles from context history."""

import logging
from config import get_config
from utils.profile_manager import profile_manager
from utils.context_extractor import message_history
from ai_providers import create_provider

logger = logging.getLogger(__name__)


class ProfileRegenerationService:
    """Service for regenerating user profiles using AI enrichment."""

    def __init__(self):
        """Initialize the profile regeneration service."""
        self.config = get_config()

    async def regenerate_all_profiles(self) -> dict:
        """Regenerate all user profiles from context history.

        Returns:
            dict: Statistics about the regeneration process
        """
        logger.info("=" * 60)
        logger.info("PROFILE REGENERATION STARTING")
        logger.info("=" * 60)

        try:
            logger.info(f"Configuration loaded: {self.config.ai_provider} / {self.config.model_name}")

            # Create AI provider
            ai_provider = create_provider(
                provider_type=self.config.ai_provider,
                api_key=self.config.api_key,
                model=self.config.model_name,
                base_url=self.config.base_url,
            )
            logger.info("AI provider initialized")

            # Get all chats from message history
            all_chats = message_history.get_all_chat_ids()
            logger.info(f"Found {len(all_chats)} chats in history")

            # Collect user messages from all chats
            user_data = {}  # user_id -> messages list
            user_info = {}  # user_id -> user info dict

            for chat_id in all_chats:
                messages = message_history.get_recent_messages(chat_id)
                if not messages:
                    continue

                # Limit to most recent 100 messages
                messages = messages[-100:]

                for msg_data in messages:
                    msg_user_id = msg_data.get("user_id", 0)
                    text = msg_data.get("text", "")

                    if msg_user_id == 0 or not text or text.startswith("/"):
                        continue

                    # Store user info from the first message we see for each user
                    if msg_user_id not in user_info:
                        user_info[msg_user_id] = {
                            "username": msg_data.get("username", ""),
                            "first_name": msg_data.get("first_name", ""),
                            "last_name": msg_data.get("last_name", ""),
                        }

                    if msg_user_id not in user_data:
                        user_data[msg_user_id] = []
                    user_data[msg_user_id].append(text)

            if not user_data:
                logger.warning("No user messages found in context history")
                return {"processed": 0, "skipped": 0, "failed": 0, "total": 0, "message": "No user messages found"}

            logger.info(f"Found {len(user_data)} users to process")

            # Process each user
            processed = 0
            skipped = 0
            failed = 0

            for user_id, messages in user_data.items():
                if len(messages) < 5:
                    logger.info(f"Skipping user {user_id} (only {len(messages)} messages)")
                    skipped += 1
                    continue

                profile = profile_manager.load_profile(user_id)

                # Update profile with user info from context history
                if user_id in user_info:
                    info = user_info[user_id]
                    profile.username = info["username"] or profile.username
                    profile.first_name = info["first_name"] or profile.first_name
                    profile.last_name = info["last_name"] or profile.last_name

                messages_text = "\n".join(messages[:30])

                # Sanitize name for logging to avoid Unicode encoding issues
                safe_name = (profile.first_name or "Unknown").encode("ascii", "ignore").decode("ascii") or "Unknown"
                logger.info(f"Processing user {user_id} ({safe_name}) - {len(messages)} messages")

                try:
                    await profile_manager.enrich_profile_with_ai(
                        user_id=user_id, recent_messages=messages_text, ai_analyzer=ai_provider
                    )
                    profile_manager.save_profile(user_id)
                    processed += 1
                    logger.info(f"[OK] User {user_id} enriched successfully")

                except Exception as e:
                    logger.error(f"[FAIL] Failed to regenerate profile for user {user_id}: {e}")
                    failed += 1

            result = {"processed": processed, "skipped": skipped, "failed": failed, "total": len(user_data)}

            logger.info("=" * 60)
            logger.info("PROFILE REGENERATION COMPLETE")
            logger.info(f"Processed: {processed}")
            logger.info(f"Skipped (<5 messages): {skipped}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Total: {len(user_data)}")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"Error during profile regeneration: {e}", exc_info=True)
            raise
