"""Message handlers for the Telegram bot."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from ai_providers import create_provider
from utils.context_extractor import message_history


logger = logging.getLogger(__name__)


# Initialize AI provider
config = get_config()
ai_provider = create_provider(
    provider_type=config.ai_provider,
    api_key=config.api_key,
    model=config.model_name
)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main message handler that processes all incoming messages.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message or not update.message.text:
        return
    
    message = update.message
    chat_id = message.chat_id
    
    # Store message in history for context extraction
    message_history.add_message(chat_id, message)
    
    # Check if it's a /joke command
    if message.text.startswith('/joke'):
        await handle_joke_command(update, context)
        return
    
    # Check if bot is mentioned
    if await is_bot_mentioned(message, config.bot_username):
        await handle_mention(update, context)
        return


async def handle_joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /joke command.
    
    The command can be used in two ways:
    - /joke - generates a random Russian joke using recent conversation context
    - /joke <context> - generates a Russian joke based on the provided context
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message:
        return
    
    message = update.message
    chat_id = message.chat_id
    
    try:
        # Parse command and extract context if provided
        command_text = message.text.strip()
        parts = command_text.split(maxsplit=1)
        
        if len(parts) > 1:
            # User provided explicit context: /joke <context>
            user_context = parts[1].strip()
            logger.info(f"Generating joke with user-provided context in chat {chat_id}")
            joke = await ai_provider.generate_joke(context=user_context, is_contextual=False)
        else:
            # No explicit context, use conversation history
            logger.info(f"Generating joke with conversation context in chat {chat_id}")
            conversation_context = message_history.get_context(
                chat_id=chat_id,
                count=config.context_messages_count
            )
            
            if conversation_context:
                joke = await ai_provider.generate_joke(context=conversation_context, is_contextual=True)
            else:
                # No context available, generate random joke
                logger.info(f"No context available, generating random joke in chat {chat_id}")
                joke = await ai_provider.generate_joke(context=None, is_contextual=False)
        
        # Send the joke
        await send_joke_response(message, joke)
        
    except Exception as e:
        logger.error(f"Error handling /joke command: {e}")
        await message.reply_text(
            "Извините, произошла ошибка при генерации анекдота. Попробуйте позже.",
            reply_to_message_id=message.message_id
        )


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot mentions in messages.
    
    When the bot is mentioned, it generates a contextual joke based on recent conversation.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message:
        return
    
    message = update.message
    chat_id = message.chat_id
    
    try:
        logger.info(f"Bot mentioned in chat {chat_id}, generating contextual joke")
        
        # Get conversation context
        conversation_context = message_history.get_context(
            chat_id=chat_id,
            count=config.context_messages_count
        )
        
        if conversation_context:
            # Generate contextual joke
            joke = await ai_provider.generate_joke(context=conversation_context, is_contextual=True)
        else:
            # No context available, generate random joke
            logger.warning(f"No context available for mention in chat {chat_id}")
            joke = await ai_provider.generate_joke(context=None, is_contextual=False)
        
        # Send the joke
        await send_joke_response(message, joke)
        
    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        await message.reply_text(
            "Извините, произошла ошибка. Попробуйте позже.",
            reply_to_message_id=message.message_id
        )


async def is_bot_mentioned(message, bot_username: str) -> bool:
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
    username_without_at = bot_username.replace('@', '').lower()
    if username_without_at in text:
        return True
    
    # Check for entities (mentions)
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention" or entity.type == "text_mention":
                mention_text = message.text[entity.offset:entity.offset + entity.length]
                if bot_username.lower() in mention_text.lower():
                    return True
    
    return False


async def send_joke_response(message, joke: str) -> None:
    """Send a joke as a reply to the message.
    
    Args:
        message: Telegram message to reply to
        joke: The joke text to send
    """
    try:
        await message.reply_text(
            joke,
            reply_to_message_id=message.message_id
        )
        logger.info(f"Successfully sent joke to chat {message.chat_id}")
    except Exception as e:
        logger.error(f"Failed to send joke: {e}")
        raise
