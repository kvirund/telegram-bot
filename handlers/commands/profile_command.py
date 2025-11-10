"""Handle /profile command to show user profile."""
import logging
import json
import os
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.profile_manager import profile_manager
from ai_providers import create_provider
from .base import Command

logger = logging.getLogger(__name__)


class ProfileCommand(Command):
    """Profile command for viewing user profiles.

    Usage:
    - /profile @username
    - /profile user_id
    - /profile FirstName

    Only administrators can use this command.
    """

    def __init__(self):
        super().__init__(
            name="profile",
            description="Show user profile (admin only)",
            admin_only=True
        )

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /profile command to show user profile.

        Usage:
        - /profile @username
        - /profile user_id
        - /profile FirstName

        Only administrators can use this command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        config = get_config()

        if not update.message or not update.message.from_user:
            return

        message = update.message
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"

        logger.info(f"User {user_id} (@{username}) requested /profile command")

        # Check admin privilege
        if user_id not in config.admin_user_ids:
            await message.reply_text(
                "❌ Only administrators can view user profiles.",
                reply_to_message_id=message.message_id
            )
            return

        try:
            # Parse command
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)

            if len(parts) < 2:
                await message.reply_text(
                    "Usage: /profile <user>\n\n"
                    "Examples:\n"
                    "• /profile @username\n"
                    "• /profile 123456789\n"
                    "• /profile John",
                    reply_to_message_id=message.message_id
                )
                return

            search_term = parts[1].strip()

            # Try to find user profile
            profile = None
            search_method = ""

            # Method 1: Try as user ID
            if search_term.isdigit():
                profile_id = int(search_term)
                profile = profile_manager.load_profile(profile_id)
                if profile and profile.user_id != 0:
                    search_method = f"ID: {profile_id}"

            # Method 2: Try as username (with or without @)
            if not profile:
                username_search = search_term.lstrip('@')
                # Search all profiles for matching username
                profiles_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    config.yaml_config.user_profiling.profile_directory,
                    "users"
                )
                if os.path.exists(profiles_dir):
                    for filename in os.listdir(profiles_dir):
                        if filename.endswith('.json'):
                            try:
                                file_user_id = int(filename.replace('user_', '').replace('.json', ''))
                                temp_profile = profile_manager.load_profile(file_user_id)
                                if (temp_profile and temp_profile.username and
                                    temp_profile.username.lower() == username_search.lower()):
                                    profile = temp_profile
                                    search_method = f"Username: @{username_search}"
                                    break
                            except:
                                continue

            # Method 3: Try as first name
            if not profile:
                if os.path.exists(profiles_dir):
                    for filename in os.listdir(profiles_dir):
                        if filename.endswith('.json'):
                            try:
                                file_user_id = int(filename.replace('user_', '').replace('.json', ''))
                                temp_profile = profile_manager.load_profile(file_user_id)
                                if (temp_profile and temp_profile.first_name and
                                    temp_profile.first_name.lower() == search_term.lower()):
                                    profile = temp_profile
                                    search_method = f"Name: {search_term}"
                                    break
                            except:
                                continue

            if not profile or profile.user_id == 0:
                await message.reply_text(
                    f"❌ No profile found for: {search_term}",
                    reply_to_message_id=message.message_id
                )
                return

            # Use AI to generate comprehensive, human-readable profile
            language = profile.language_preference or 'ru'

            try:
                profile_summary = await _generate_ai_profile_summary(profile, language, config)

                await message.reply_text(
                    profile_summary,
                    reply_to_message_id=message.message_id,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error generating AI profile summary: {e}")
                # Fallback to basic display
                profile_text = f"👤 **User: {profile.first_name}** (@{profile.username})\n"
                profile_text += f"🆔 ID: `{profile.user_id}`\n"
                profile_text += f"📊 Messages: {profile.message_count}\n"

                await message.reply_text(
                    profile_text,
                    reply_to_message_id=message.message_id,
                    parse_mode='Markdown'
                )
            logger.info(f"Profile displayed for user {profile.user_id} by admin {user_id}")

        except Exception as e:
            logger.error(f"Error in /profile command: {e}")
            await message.reply_text(
                f"❌ Error: {str(e)}",
                reply_to_message_id=message.message_id
            )


# Create and register the command instance
profile_command = ProfileCommand()


# Legacy function for backward compatibility during transition
async def handle_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await profile_command.execute(update, context)


async def _generate_ai_profile_summary(profile, language: str, config) -> str:
    """Generate comprehensive AI profile summary in target language.

    Args:
        profile: UserProfile object
        language: Target language ('ru' or 'en')
        config: Configuration object

    Returns:
        str: Formatted profile summary
    """
    # Prepare profile data as JSON for AI
    profile_data = {
        "basic_info": {
            "user_id": profile.user_id,
            "username": profile.username,
            "first_name": profile.first_name,
            "message_count": profile.message_count,
            "language": profile.language_preference
        },
        "interests": profile.interests,
        "speaking_style": {
            "tone": profile.speaking_style.tone,
            "vocabulary": profile.speaking_style.vocabulary_level,
            "emoji_usage": profile.speaking_style.emoji_usage
        },
        "humor_type": profile.humor_type,
        "weaknesses": {
            "technical": profile.weaknesses.technical,
            "personal": profile.weaknesses.personal
        },
        "patterns": {
            "common_mistakes": profile.patterns.common_mistakes,
            "embarrassing_moments": profile.embarrassing_moments
        }
    }

    # Build AI prompt
    if language == 'ru':
        prompt = f"""Создай подробное, читаемое описание профиля пользователя на основе этих данных:

{json.dumps(profile_data, ensure_ascii=False, indent=2)}

Создай ПОЛНЫЙ психологический портрет пользователя в свободной форме. Включи:
- Краткую характеристику личности
- Интересы и увлечения
- Стиль общения и юмор
- Технические и личные слабости
- Характерные ошибки и паттерны поведения
- Забавные или неловкие моменты

Пиши естественно и занимательно, как будто описываешь знакомого человека. Используй эмодзи.

КРИТИЧНО ВАЖНО: Используй ТОЛЬКО эти HTML теги: <b>bold</b>, <i>italic</i>, <u>underline</u>, <s>strikethrough</s>, <code>code</code>, <pre>preformatted</pre>, <a href="...">link</a>.
ЗАПРЕЩЕНО использовать: <h1>, <h2>, <h3>, <p>, <div>, <span>, <br>, <strong>, <em> или любые другие HTML теги.

Начни с "<b>👤 {profile.first_name}</b>" и используй <b> для выделения важных частей текста вместо заголовков."""
    else:
        prompt = f"""Create a detailed, readable profile description based on this data:

{json.dumps(profile_data, ensure_ascii=False, indent=2)}

Create a FULL psychological portrait of the user in narrative form. Include:
- Brief personality characterization
- Interests and hobbies
- Communication style and humor
- Technical and personal weaknesses
- Characteristic mistakes and behavior patterns
- Funny or awkward moments

Write naturally and engagingly, as if describing an acquaintance. Use emoji.

CRITICALLY IMPORTANT: Use ONLY these HTML tags: <b>bold</b>, <i>italic</i>, <u>underline</u>, <s>strikethrough</s>, <code>code</code>, <pre>preformatted</pre>, <a href="...">link</a>.
FORBIDDEN to use: <h1>, <h2>, <h3>, <p>, <div>, <span>, <br>, <strong>, <em> or any other HTML tags.

Start with "<b>👤 {profile.first_name}</b>" and use <b> to highlight important parts of text instead of headers."""

    try:
        ai_provider = create_provider(
            provider_type=config.ai_provider,
            api_key=config.api_key,
            model=config.model_name,
            base_url=config.base_url
        )
        summary = await ai_provider.free_request(
            user_message=prompt,
            system_message="You are a skilled profiler. Create comprehensive, engaging profiles."
        )

        # Sanitize the response to remove unsupported HTML tags
        import re
        # Remove unsupported HTML tags but keep supported ones
        # Supported: <b>, <i>, <u>, <s>, <code>, <pre>, <a>
        # Remove: <h1>, <h2>, <h3>, <p>, <div>, <span>, <br>, <strong>, <em>, etc.
        unsupported_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th']
        for tag in unsupported_tags:
            # Remove opening and closing tags
            summary = re.sub(rf'</?{tag}[^>]*>', '', summary, flags=re.IGNORECASE)

        return summary
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        raise
