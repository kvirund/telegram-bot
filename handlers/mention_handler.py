"""Handle bot mentions in messages."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.context_extractor import message_history
from ai_providers import create_provider

logger = logging.getLogger(__name__)


def is_bot_mentioned(message, bot_username: str) -> bool:
    """Check if the bot is mentioned in the message.

    Args:
        message: Telegram message object
        bot_username: Bot's username (e.g., "@jokebot")

    Returns:
        bool: True if bot is mentioned, False otherwise
    """
    if not message or not message.text:
        return False

    text = message.text.lower()

    # Check for @username mention
    if bot_username.lower() in text:
        return True

    # Check for username without @ symbol
    username_without_at = bot_username.replace("@", "").lower()
    if username_without_at in text:
        return True

    # Check for entities (mentions)
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention" or entity.type == "text_mention":
                mention_text = message.text[entity.offset : entity.offset + entity.length]
                if bot_username.lower() in mention_text.lower():
                    return True

    return False


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot mentions in messages.

    When the bot is mentioned, it responds using the mention_response system prompt
    with conversation context.

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    config = get_config()
    ai_provider = create_provider(
        provider_type=config.ai_provider, api_key=config.api_key, model=config.model_name, base_url=config.base_url
    )

    if not update.message:
        return

    message = update.message
    chat_id = message.chat_id
    user_message = message.text or ""

    try:
        logger.info(f"Bot mentioned in chat {chat_id}, generating response")

        # Get conversation context
        conversation_context = message_history.get_context(chat_id=chat_id, count=config.context_messages_count)

        # Get the mention_response system prompt
        system_prompt = config.yaml_config.system_prompts.mention_response

        # Build user message with context
        if conversation_context:
            context_aware_message = f"Контекст разговора:\n{conversation_context}\n\nПоследнее сообщение: {user_message}\n\nОтветь на сообщение в контексте разговора:"
        else:
            context_aware_message = f"Сообщение: {user_message}\n\nОтветь на это сообщение:"

        # Generate response using the mention_response prompt
        response = await ai_provider.free_request(user_message=context_aware_message, system_message=system_prompt)

        # Send the response
        await message.reply_text(response, reply_to_message_id=message.message_id)
        logger.info(f"Successfully sent mention response to chat {chat_id}")

    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        await message.reply_text("Иди нахуй, у меня ошибка.", reply_to_message_id=message.message_id)
