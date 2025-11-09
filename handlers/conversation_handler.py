"""Handle private chat conversations with context awareness."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.context_extractor import message_history
from ai_providers import create_provider

logger = logging.getLogger(__name__)


def is_mostly_cyrillic(text: str) -> bool:
    """Check if text is mostly Cyrillic (Russian).

    Args:
        text: Text to check

    Returns:
        bool: True if text is mostly Cyrillic
    """
    if not text:
        return False

    cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
    total_letters = sum(1 for char in text if char.isalpha())

    return total_letters > 0 and (cyrillic_count / total_letters) > 0.5


def is_mostly_english(text: str) -> bool:
    """Check if text is mostly English.

    Args:
        text: Text to check

    Returns:
        bool: True if text is mostly English (Latin alphabet)
    """
    if not text:
        return False

    latin_count = sum(1 for char in text if 'a' <= char.lower() <= 'z')
    total_letters = sum(1 for char in text if char.isalpha())

    return total_letters > 0 and (latin_count / total_letters) > 0.5


def detect_conversation_language(context: str, current_message: str) -> str:
    """Detect the language of the conversation.

    Args:
        context: Previous conversation context
        current_message: Current user message

    Returns:
        str: Detected language ('russian', 'english', or 'russian' as default)
    """
    # Combine context and current message for detection
    combined_text = f"{context} {current_message}" if context else current_message

    if not combined_text:
        return "russian"  # Default to Russian

    # Count Cyrillic and Latin characters
    cyrillic_count = sum(1 for char in combined_text if '\u0400' <= char <= '\u04FF')
    latin_count = sum(1 for char in combined_text if 'a' <= char.lower() <= 'z')
    total_letters = cyrillic_count + latin_count

    if total_letters == 0:
        return "russian"  # Default to Russian if no letters

    # Determine predominant language
    if cyrillic_count > latin_count:
        return "russian"
    elif latin_count > cyrillic_count * 2:  # Significantly more English
        return "english"
    else:
        return "russian"  # Default to Russian for mixed or unclear cases


async def handle_private_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle private chat conversations with context awareness.

    Responds to every non-command message in private chats using conversation context.
    Defaults to Russian but adapts to user's language.

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    config = get_config()
    ai_provider = create_provider(
        provider_type=config.ai_provider,
        api_key=config.api_key,
        model=config.model_name,
        base_url=config.base_url
    )

    if not update.message:
        return

    message = update.message
    chat_id = message.chat_id
    user_message = message.text

    try:
        logger.info(f"Processing private conversation in chat {chat_id}")

        # Get conversation context (last N messages)
        conversation_context = message_history.get_context(
            chat_id=chat_id,
            count=config.yaml_config.conversation_monitoring.context_window_size
        )

        # Detect language from recent messages
        detected_language = detect_conversation_language(conversation_context, user_message)

        # Prepare language-specific instructions
        if detected_language == "russian":
            language_instruction = "ВАЖНО: Отвечай ТОЛЬКО на русском языке, если только пользователь не использует другой язык явно."
        else:
            language_instruction = f"IMPORTANT: Respond in {detected_language} to match the user's language."

        # Prepare the prompt with context
        if conversation_context:
            system_prompt = (
                "You are a helpful, witty, and engaging conversational AI assistant. "
                "You remember the conversation context and respond naturally. "
                "Keep your responses concise and relevant. "
                "You can be humorous when appropriate but remain helpful.\n\n"
                f"{language_instruction}"
            )

            # Build user message with context
            context_aware_message = f"Conversation history:\n{conversation_context}\n\nUser: {user_message}\n\nRespond naturally to the user's latest message:"

            response = await ai_provider.free_request(
                user_message=context_aware_message,
                system_message=system_prompt
            )
        else:
            # No context yet, respond to first message
            # Check if first message is in Russian
            if is_mostly_cyrillic(user_message):
                language_instruction = "ВАЖНО: Отвечай ТОЛЬКО на русском языке."
            else:
                # Detect language of first message
                if is_mostly_english(user_message):
                    language_instruction = "IMPORTANT: Respond in English."
                else:
                    language_instruction = "ВАЖНО: Отвечай на русском языке по умолчанию, но адаптируйся к языку пользователя."

            system_prompt = (
                "You are a helpful, witty, and engaging conversational AI assistant.\n\n"
                f"{language_instruction}"
            )

            response = await ai_provider.free_request(
                user_message=user_message,
                system_message=system_prompt
            )

        # Send response
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id
        )
        logger.info(f"Successfully sent conversational response to chat {chat_id}")

    except Exception as e:
        logger.error(f"Error in private conversation: {e}")
        await message.reply_text(
            "Sorry, I encountered an error. Please try again.",
            reply_to_message_id=message.message_id
        )
