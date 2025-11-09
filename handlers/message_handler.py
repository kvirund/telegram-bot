"""Message handlers for the Telegram bot."""
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from ai_providers import create_provider
from utils.context_extractor import message_history
from utils.profile_manager import profile_manager
from utils.autonomous_commenter import AutonomousCommenter
from utils.reaction_manager import get_reaction_manager


logger = logging.getLogger(__name__)


# Initialize AI provider and autonomous systems
config = get_config()
reaction_manager = get_reaction_manager(config)
ai_provider = create_provider(
    provider_type=config.ai_provider,
    api_key=config.api_key,
    model=config.model_name,
    base_url=config.base_url
)

# Initialize autonomous commenter
autonomous_commenter = AutonomousCommenter(config, profile_manager)

# Auto-save profiles periodically
async def auto_save_profiles():
    """Background task to periodically save profiles."""
    while True:
        try:
            interval = config.yaml_config.user_profiling.auto_save_interval_seconds
            await asyncio.sleep(interval)
            if config.yaml_config.user_profiling.enabled:
                profile_manager.save_all_profiles()
                logger.info("Auto-saved all profiles")
        except Exception as e:
            logger.error(f"Error in auto-save profiles: {e}")


# Auto-save context history periodically
async def auto_save_context():
    """Background task to periodically save context history."""
    while True:
        try:
            # Save every 5 minutes (300 seconds)
            await asyncio.sleep(300)
            message_history.save_all()
            message_history.cleanup_expired()
            logger.info("Auto-saved context history and cleaned up expired messages")
        except Exception as e:
            logger.error(f"Error in auto-save context: {e}")


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
    is_private = message.chat.type == "private"
    bot_user_id = context.bot.id
    
    # Update user profile (if profiling enabled and not bot's own message)
    if (config.yaml_config.user_profiling.enabled and 
        message.from_user and 
        message.from_user.id != bot_user_id):
        try:
            profile_manager.update_profile_from_message(message)
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
    
    # Store message in history for context extraction (both private and group chats)
    message_history.add_message(chat_id, message)
    
    # Track message for autonomous commenting (only in group chats)
    if not is_private and message.from_user and message.from_user.id != bot_user_id:
        autonomous_commenter.add_message(chat_id, message)
    
    # Check if it's a /joke command
    if message.text.startswith('/joke'):
        await handle_joke_command(update, context, is_private)
        return
    
    # Check if it's a /ask command
    if message.text.startswith('/ask'):
        await handle_ask_command(update, context)
        return
    
    # Check if it's a /reload command
    if message.text.startswith('/reload'):
        await handle_reload_command(update, context)
        return
    
    # Check if it's a /comment command
    if message.text.startswith('/comment'):
        await handle_comment_command(update, context)
        return
    
    # Check if it's a /help command
    if message.text.startswith('/help'):
        await handle_help_command(update, context)
        return
    
    # Check if it's a /context command
    if message.text.startswith('/context'):
        await handle_context_command(update, context)
        return
    
    # Check if it's a /profile command
    if message.text.startswith('/profile'):
        await handle_profile_command(update, context)
        return
    
    # Check if it's a /chats command
    if message.text.startswith('/chats'):
        await handle_chats_command(update, context)
        return
    
    # In private chats, respond conversationally to all messages
    if is_private:
        await handle_private_conversation(update, context)
        return
    
    # In group chats, check if bot is mentioned
    if await is_bot_mentioned(message, config.bot_username):
        await handle_mention(update, context)
        return
    
    # Check for autonomous commenting opportunity (not in response to commands/mentions)
    if (not is_private and 
        config.yaml_config.autonomous_commenting.enabled and
        not message.text.startswith('/')):
        await check_and_make_autonomous_comment(update, context)
    
    # Check for autonomous reaction opportunity (group chats only)
    if (not is_private and 
        message.from_user and 
        message.from_user.id != bot_user_id and
        not message.text.startswith('/')):
        await check_and_add_reaction(update, context)


async def handle_joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE, is_private: bool = False) -> None:
    """Handle /joke command.
    
    The command can be used in two ways:
    - /joke - generates a random Russian joke (in groups: using context, in private: random)
    - /joke <context> - generates a Russian joke based on the provided context
    
    Args:
        update: Telegram update object
        context: Telegram context object
        is_private: Whether this is a private chat
    """
    if not update.message:
        return
    
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username if message.from_user else "Unknown"
    
    logger.info(f"User {user_id} (@{username}) requested /joke command in chat {chat_id}")
    
    try:
        # Parse command and extract context if provided
        command_text = message.text.strip()
        parts = command_text.split(maxsplit=1)
        
        if len(parts) > 1:
            # User provided explicit context: /joke <context>
            user_context = parts[1].strip()
            logger.info(f"Generating joke with user-provided context in chat {chat_id}")
            joke = await ai_provider.generate_joke(context=user_context, is_contextual=False)
        elif not is_private:
            # In groups, use conversation history
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
        else:
            # In private chats without context, generate random joke
            logger.info(f"Generating random joke in private chat {chat_id}")
            joke = await ai_provider.generate_joke(context=None, is_contextual=False)
        
        # Send the joke
        await send_joke_response(message, joke)
        
    except Exception as e:
        logger.error(f"Error handling /joke command: {e}")
        await message.reply_text(
            "Извините, произошла ошибка при генерации анекдота. Попробуйте позже.",
            reply_to_message_id=message.message_id
        )


async def handle_ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask command for free-form requests.
    
    Usage formats:
    - /ask <user_message> - sends user message only
    - /ask system:<system_message> user:<user_message> - sends both system and user messages
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message:
        return
    
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username if message.from_user else "Unknown"
    
    logger.info(f"User {user_id} (@{username}) requested /ask command in chat {chat_id}")
    
    try:
        # Parse command
        command_text = message.text.strip()
        parts = command_text.split(maxsplit=1)
        
        if len(parts) < 2:
            await message.reply_text(
                "Использование:\n"
                "/ask <ваш запрос> - простой запрос\n"
                "/ask system:<системное сообщение> user:<запрос пользователя> - с системным промптом",
                reply_to_message_id=message.message_id
            )
            return
        
        request_text = parts[1].strip()
        system_message = None
        user_message = None
        
        # Check if using system/user format
        if 'system:' in request_text and 'user:' in request_text:
            # Extract system and user messages
            system_start = request_text.find('system:') + 7
            user_start = request_text.find('user:')
            
            if system_start < user_start:
                system_message = request_text[system_start:user_start].strip()
                user_message = request_text[user_start + 5:].strip()
            else:
                await message.reply_text(
                    "Неверный формат. Используйте: /ask system:<текст> user:<текст>",
                    reply_to_message_id=message.message_id
                )
                return
        else:
            # Simple user message only
            user_message = request_text
        
        if not user_message:
            await message.reply_text(
                "Запрос пользователя не может быть пустым",
                reply_to_message_id=message.message_id
            )
            return
        
        logger.info(f"Processing free request in chat {chat_id}")
        
        # Make the request
        response = await ai_provider.free_request(
            user_message=user_message,
            system_message=system_message
        )
        
        # Send response
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id
        )
        logger.info(f"Successfully sent response to chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error handling /ask command: {e}")
        await message.reply_text(
            "Извините, произошла ошибка при обработке запроса. Попробуйте позже.",
            reply_to_message_id=message.message_id
        )


async def handle_reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reload command to reload configuration.
    
    This reloads both .env and config.yaml files without restarting the bot.
    Only authorized admin users can execute this command.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    global config, autonomous_commenter
    
    if not update.message or not update.message.from_user:
        return
    
    message = update.message
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    logger.info(f"User {user_id} (@{username}) requested /reload command")
    
    # Check if command is sent in private chat only
    if message.chat.type != "private":
        logger.warning(f"/reload command attempted in group chat {message.chat_id} by user {user_id}")
        await message.reply_text(
            "❌ This command can only be used in private chat with the bot.",
            reply_to_message_id=message.message_id
        )
        return
    
    # Check if user is authorized admin
    if user_id not in config.admin_user_ids:
        logger.warning(f"Unauthorized /reload attempt by user {user_id} (@{message.from_user.username})")
        await message.reply_text(
            "❌ Unauthorized. Only bot administrators can reload configuration.",
            reply_to_message_id=message.message_id
        )
        return
    
    try:
        logger.info(f"Reloading configuration requested by authorized user {user_id}")
        
        # Reload configuration
        from config import reload_config
        
        old_config = config
        config = reload_config()
        
        # Update autonomous commenter with new config
        autonomous_commenter.config = config
        
        # Build response message
        changes = []
        if old_config.yaml_config.autonomous_commenting.enabled != config.yaml_config.autonomous_commenting.enabled:
            status = "ENABLED" if config.yaml_config.autonomous_commenting.enabled else "DISABLED"
            changes.append(f"Autonomous commenting: {status}")
        
        if old_config.yaml_config.autonomous_commenting.roasting_aggression != config.yaml_config.autonomous_commenting.roasting_aggression:
            changes.append(f"Roasting aggression: {config.yaml_config.autonomous_commenting.roasting_aggression}")
        
        if old_config.yaml_config.user_profiling.enabled != config.yaml_config.user_profiling.enabled:
            status = "ENABLED" if config.yaml_config.user_profiling.enabled else "DISABLED"
            changes.append(f"User profiling: {status}")
        
        response = "✅ Configuration reloaded successfully!\n\n"
        if changes:
            response += "Notable changes:\n" + "\n".join(f"- {change}" for change in changes)
        else:
            response += "No changes detected in configuration."
        
        response += f"\n\nCurrent settings:\n"
        response += f"- Autonomous commenting: {'ENABLED' if config.yaml_config.autonomous_commenting.enabled else 'DISABLED'}\n"
        response += f"- Roasting: {'ENABLED' if config.yaml_config.autonomous_commenting.roasting_enabled else 'DISABLED'}\n"
        response += f"- Aggression: {config.yaml_config.autonomous_commenting.roasting_aggression}\n"
        response += f"- User profiling: {'ENABLED' if config.yaml_config.user_profiling.enabled else 'DISABLED'}"
        
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id
        )
        
        logger.info("Configuration reloaded successfully")
        
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        await message.reply_text(
            f"❌ Error reloading configuration: {str(e)}",
            reply_to_message_id=message.message_id
        )


async def handle_comment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /comment command to force an autonomous comment.
    
    This forces the bot to generate and post an autonomous comment immediately
    in a specified chat, using current context. Only authorized admin users can
    execute this command, and it must be used in private chat.
    
    Usage: /comment <chat_id>
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    global config, autonomous_commenter
    
    if not update.message or not update.message.from_user:
        return
    
    message = update.message
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    logger.info(f"User {user_id} (@{username}) requested /comment command")
    
    # Check if command is sent in private chat only
    if message.chat.type != "private":
        logger.warning(f"/comment command attempted in group chat {message.chat_id} by user {user_id}")
        await message.reply_text(
            "❌ This command can only be used in private chat with the bot.",
            reply_to_message_id=message.message_id
        )
        return
    
    # Check if user is authorized admin
    if user_id not in config.admin_user_ids:
        logger.warning(f"Unauthorized /comment attempt by user {user_id} (@{message.from_user.username})")
        await message.reply_text(
            "❌ Unauthorized. Only bot administrators can use this command.",
            reply_to_message_id=message.message_id
        )
        return
    
    try:
        # Parse command to get chat ID
        command_text = message.text.strip()
        parts = command_text.split(maxsplit=1)
        
        if len(parts) < 2:
            await message.reply_text(
                "Usage: /comment <chat_id>\n\n"
                "Forces the bot to generate an autonomous comment in the specified chat.\n"
                "Example: /comment -1001234567890",
                reply_to_message_id=message.message_id
            )
            return
        
        try:
            target_chat_id = int(parts[1].strip())
        except ValueError:
            await message.reply_text(
                "❌ Invalid chat ID. Please provide a numeric chat ID.\n"
                "Example: /comment -1001234567890",
                reply_to_message_id=message.message_id
            )
            return
        
        logger.info(f"Forcing autonomous comment in chat {target_chat_id} by admin {user_id}")
        
        # Generate comment for target chat
        bot_user_id = context.bot.id
        comment = await autonomous_commenter.generate_comment(
            chat_id=target_chat_id,
            ai_provider=ai_provider,
            bot_user_id=bot_user_id
        )
        
        if not comment:
            await message.reply_text(
                f"❌ Failed to generate comment for chat {target_chat_id}.\n"
                "Possible reasons:\n"
                "- No message history available for this chat\n"
                "- Chat not found in history\n"
                "- AI generation failed",
                reply_to_message_id=message.message_id
            )
            return
        
        # Send comment to target chat
        try:
            if comment.reply_to_message_id:
                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=comment.text,
                    reply_to_message_id=comment.reply_to_message_id
                )
                await message.reply_text(
                    f"✅ Comment sent to chat {target_chat_id} as reply to message {comment.reply_to_message_id}",
                    reply_to_message_id=message.message_id
                )
            else:
                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=comment.text
                )
                await message.reply_text(
                    f"✅ Standalone comment sent to chat {target_chat_id}",
                    reply_to_message_id=message.message_id
                )
            
            # Mark that we commented
            autonomous_commenter.mark_commented(target_chat_id)
            
            # Record roast if applicable
            if comment.target_user_id and comment.comment_type == "roast":
                profile_manager.record_roast(
                    target_user_id=comment.target_user_id,
                    roast_topic=comment.comment_type,
                    success=True
                )
            
            logger.info(f"Successfully sent forced comment to chat {target_chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to send comment to chat {target_chat_id}: {e}")
            await message.reply_text(
                f"❌ Failed to send comment to chat {target_chat_id}: {str(e)}\n"
                "The bot may not have access to this chat.",
                reply_to_message_id=message.message_id
            )
        
    except Exception as e:
        logger.error(f"Error in /comment command: {e}")
        await message.reply_text(
            f"❌ Error: {str(e)}",
            reply_to_message_id=message.message_id
        )


async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show available commands based on user privilege level.
    
    Supports language detection and manual language selection:
    - /help - Auto-detect language from user profile
    - /help ru - Force Russian
    - /help en - Force English
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message or not update.message.from_user:
        return
    
    message = update.message
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    
    logger.info(f"User {user_id} ({username}) requested /help command")
    
    # Parse command for language parameter
    command_text = message.text.strip()
    parts = command_text.split(maxsplit=1)
    forced_language = parts[1].lower() if len(parts) > 1 else None
    
    # Determine language
    if forced_language in ['ru', 'russian', 'русский']:
        language = 'ru'
    elif forced_language in ['en', 'english', 'английский']:
        language = 'en'
    else:
        # Auto-detect from user profile
        user_profile = profile_manager.load_profile(user_id)
        if user_profile and user_profile.language_preference:
            language = 'ru' if user_profile.language_preference == 'ru' else 'en'
        else:
            # Default to Russian for Russian-speaking chats
            language = 'ru'
    
    # Determine privilege level
    is_admin = user_id in config.admin_user_ids
    
    # Build help message in selected language
    if language == 'ru':
        help_text = _build_russian_help(user_id, is_admin)
    else:
        help_text = _build_english_help(user_id, is_admin)
    
    await message.reply_text(
        help_text,
        reply_to_message_id=message.message_id,
        parse_mode='HTML'
    )
    logger.info(f"Sent {language} help to user {user_id} ({username})")


def _build_russian_help(user_id: int, is_admin: bool) -> str:
    """Build Russian help message.
    
    Args:
        user_id: User ID
        is_admin: Whether user is admin
        
    Returns:
        str: Russian help text
    """
    access_level = "Администратор" if is_admin else "Пользователь"
    
    help_text = "🤖 <b>Помощь по Telegram Joke Bot</b>\n\n"
    help_text += f"👤 <b>Ваш уровень доступа:</b> {access_level}\n"
    help_text += f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>\n\n"
    
    # AI Provider info
    help_text += f"🤖 <b>AI Провайдер:</b> {config.ai_provider.upper()}\n"
    help_text += f"📊 <b>Модель:</b> {config.model_name}\n\n"
    
    # Основные команды
    help_text += "📋 <b>Доступные команды:</b>\n\n"
    help_text += "<b>Шутки и разговор:</b>\n"
    help_text += "/joke - Сгенерировать анекдот из контекста\n"
    help_text += "/joke &lt;тема&gt; - Сгенерировать анекдот на тему\n"
    help_text += "/ask &lt;вопрос&gt; - Свободный запрос к ИИ\n"
    help_text += "/help [ru/en] - Показать эту справку\n\n"
    
    help_text += "<b>Взаимодействие с ботом:</b>\n"
    help_text += "• Упомяните бота в группе для ответа\n"
    
    # Dynamic features based on config
    if config.yaml_config.autonomous_commenting.enabled:
        help_text += "• ✅ Бот автономно комментирует в группах\n"
        if config.yaml_config.autonomous_commenting.roasting_enabled:
            aggression = int(config.yaml_config.autonomous_commenting.roasting_aggression * 100)
            help_text += f"  - Режим роастинга: {aggression}% агрессии\n"
        if config.yaml_config.autonomous_commenting.use_ai_decision:
            help_text += "  - Использует AI для решений\n"
    else:
        help_text += "• ❌ Автономные комментарии отключены\n"
    
    if config.yaml_config.reaction_system.enabled and config.yaml_config.reaction_system.add_own_reactions:
        help_text += f"• ✅ Бот добавляет реакции ({int(config.yaml_config.reaction_system.reaction_probability * 100)}% шанс)\n"
    else:
        help_text += "• ❌ Реакции отключены\n"
    
    if config.yaml_config.user_profiling.enabled:
        help_text += "• ✅ Профилирование пользователей активно\n"
        help_text += "  - AI анализ личности\n"
        help_text += "  - Отслеживание слабостей\n"
    else:
        help_text += "• ❌ Профилирование отключено\n"
    
    help_text += "• Приватный чат для разговоров\n\n"
    
    # Админские команды
    if is_admin:
        help_text += "🔐 <b>Команды администратора:</b>\n"
        help_text += "/reload - Перезагрузить конфигурацию\n"
        help_text += "/comment &lt;chat_id&gt; - Принудительный комментарий\n"
        help_text += "/context [chat_id] - Очистить контекст чата\n"
        help_text += "/profile &lt;пользователь&gt; - Показать профиль\n"
        help_text += "/chats - Список всех активных чатов\n\n"
        
        help_text += "<b>Использование /profile:</b>\n"
        help_text += "• /profile @username\n"
        help_text += "• /profile user_id\n"
        help_text += "• /profile Имя\n\n"
    
    help_text += "ℹ️ <b>Возможности:</b>\n"
    help_text += "• Контекстные ответы\n"
    help_text += "• Профилирование пользователей\n"
    help_text += "• Автономные комментарии с ИИ\n"
    help_text += "• Поддержка нескольких языков\n"
    
    return help_text


def _build_english_help(user_id: int, is_admin: bool) -> str:
    """Build English help message.
    
    Args:
        user_id: User ID
        is_admin: Whether user is admin
        
    Returns:
        str: English help text
    """
    access_level = "Administrator" if is_admin else "User"
    
    help_text = "🤖 <b>Telegram Joke Bot Help</b>\n\n"
    help_text += f"👤 <b>Your Access Level:</b> {access_level}\n"
    help_text += f"🆔 <b>Your ID:</b> <code>{user_id}</code>\n\n"
    
    # Basic commands
    help_text += "📋 <b>Available Commands:</b>\n\n"
    help_text += "<b>Jokes &amp; Conversation:</b>\n"
    help_text += "/joke - Generate joke from context\n"
    help_text += "/joke &lt;topic&gt; - Generate joke about topic\n"
    help_text += "/ask &lt;question&gt; - Free-form AI request\n"
    help_text += "/help [ru/en] - Show this help message\n\n"
    
    help_text += "<b>Bot Interaction:</b>\n"
    help_text += "• Mention bot in group for response\n"
    help_text += "• Bot autonomously comments in groups\n"
    help_text += "• Bot adds reactions to messages\n"
    help_text += "• Private chat for conversations\n\n"
    
    # Admin commands
    if is_admin:
        help_text += "🔐 <b>Admin Commands:</b>\n"
        help_text += "/reload - Reload configuration\n"
        help_text += "/comment &lt;chat_id&gt; - Force comment\n"
        help_text += "/context [chat_id] - Clear chat context\n"
        help_text += "/profile &lt;user&gt; - Show user profile\n"
        help_text += "/chats - List all active chats\n\n"
        
        help_text += "<b>Profile Command Usage:</b>\n"
        help_text += "• /profile @username\n"
        help_text += "• /profile user_id\n"
        help_text += "• /profile FirstName\n\n"
    
    help_text += "ℹ️ <b>Features:</b>\n"
    help_text += "• Context-aware responses\n"
    help_text += "• User profiling &amp; tracking\n"
    help_text += "• AI-powered autonomous comments\n"
    help_text += "• Multi-language support\n"
    
    return help_text


async def handle_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /context command to reset/clear conversation context.
    
    Usage:
    - /context - Clear context for current chat
    - /context <chat_id> - Clear context for specified chat (admin only)
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message or not update.message.from_user:
        return
    
    message = update.message
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    current_chat_id = message.chat_id
    
    logger.info(f"User {user_id} (@{username}) requested /context command in chat {current_chat_id}")
    
    try:
        # Parse command
        command_text = message.text.strip()
        parts = command_text.split(maxsplit=1)
        
        # Determine target chat
        if len(parts) > 1:
            # Admin wants to clear specific chat
            if user_id not in config.admin_user_ids:
                await message.reply_text(
                    "❌ Only administrators can clear context for other chats.",
                    reply_to_message_id=message.message_id
                )
                return
            
            try:
                target_chat_id = int(parts[1].strip())
            except ValueError:
                await message.reply_text(
                    "❌ Invalid chat ID. Usage: /context <chat_id>",
                    reply_to_message_id=message.message_id
                )
                return
        else:
            # Clear current chat context
            target_chat_id = current_chat_id
        
        # Get context stats before clearing
        context_messages = message_history.get_recent_messages(target_chat_id)
        message_count = len(context_messages) if context_messages else 0
        
        # Clear context
        message_history.clear_chat_history(target_chat_id)
        
        # Also reset autonomous commenter state for this chat
        if target_chat_id in autonomous_commenter.chat_states:
            del autonomous_commenter.chat_states[target_chat_id]
        
        logger.info(f"Context cleared for chat {target_chat_id} by user {user_id} ({message_count} messages)")
        
        await message.reply_text(
            f"✅ Context cleared for chat `{target_chat_id}`\n"
            f"📊 Removed {message_count} messages from history\n"
            f"🔄 Autonomous commenter state reset",
            reply_to_message_id=message.message_id,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in /context command: {e}")
        await message.reply_text(
            f"❌ Error: {str(e)}",
            reply_to_message_id=message.message_id
        )


async def handle_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            username = search_term.lstrip('@')
            # Search all profiles for matching username
            import os
            profiles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                       config.yaml_config.user_profiling.profile_directory, "users")
            if os.path.exists(profiles_dir):
                for filename in os.listdir(profiles_dir):
                    if filename.endswith('.json'):
                        try:
                            file_user_id = int(filename.replace('user_', '').replace('.json', ''))
                            temp_profile = profile_manager.load_profile(file_user_id)
                            if temp_profile and temp_profile.username and temp_profile.username.lower() == username.lower():
                                profile = temp_profile
                                search_method = f"Username: @{username}"
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
                            if temp_profile and temp_profile.first_name and temp_profile.first_name.lower() == search_term.lower():
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
            profile_summary = await _generate_ai_profile_summary(profile, language)
            
            await message.reply_text(
                profile_summary,
                reply_to_message_id=message.message_id,
                parse_mode='Markdown'
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


async def handle_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chats command to list all chats where the bot is present.
    
    Only administrators can use this command.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message or not update.message.from_user:
        return
    
    message = update.message
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    logger.info(f"User {user_id} (@{username}) requested /chats command")
    
    # Check admin privilege
    if user_id not in config.admin_user_ids:
        await message.reply_text(
            "❌ Only administrators can view chat list.",
            reply_to_message_id=message.message_id
        )
        return
    
    try:
        # Get all chats from context history
        all_chats = message_history.get_all_chat_ids()
        
        if not all_chats:
            await message.reply_text(
                "📭 No active chats found.\n\nThe bot hasn't received messages in any chats yet.",
                reply_to_message_id=message.message_id
            )
            return
        
        # Build response using HTML instead of Markdown for better compatibility
        response = f"💬 <b>Active Chats</b> ({len(all_chats)})\n\n"
        
        # Try to get chat information for each chat
        for chat_id in sorted(all_chats):
            try:
                # Get chat info
                chat = await context.bot.get_chat(chat_id)
                chat_type = chat.type
                
                # Format chat name (escape HTML special chars)
                if chat_type == "private":
                    chat_name = f"{chat.first_name or 'Private'}"
                    if chat.username:
                        chat_name += f" (@{chat.username})"
                    chat_icon = "👤"
                elif chat_type in ["group", "supergroup"]:
                    chat_name = chat.title or "Group"
                    chat_icon = "👥"
                elif chat_type == "channel":
                    chat_name = chat.title or "Channel"
                    chat_icon = "📢"
                else:
                    chat_name = "Unknown"
                    chat_icon = "❓"
                
                # Escape HTML special characters in chat name
                import html
                chat_name = html.escape(chat_name)
                
                # Get message count
                recent_messages = message_history.get_recent_messages(chat_id)
                msg_count = len(recent_messages) if recent_messages else 0
                
                response += f"{chat_icon} <b>{chat_name}</b>\n"
                response += f"   • ID: <code>{chat_id}</code>\n"
                response += f"   • Type: {chat_type}\n"
                response += f"   • Messages: {msg_count}\n\n"
                
            except Exception as e:
                # Chat might be inaccessible or bot was removed
                logger.warning(f"Could not get info for chat {chat_id}: {e}")
                response += f"❓ <b>Unknown Chat</b>\n"
                response += f"   • ID: <code>{chat_id}</code>\n"
                response += f"   • Status: Inaccessible\n\n"
        
        # Send response (might be long, so check length)
        if len(response) > 4000:
            # Split into multiple messages
            parts = []
            current = ""
            for line in response.split('\n\n'):
                if len(current) + len(line) + 2 > 4000:
                    parts.append(current)
                    current = line + '\n\n'
                else:
                    current += line + '\n\n'
            if current:
                parts.append(current)
            
            for i, part in enumerate(parts):
                if i == 0:
                    await message.reply_text(
                        part,
                        reply_to_message_id=message.message_id,
                        parse_mode='HTML'
                    )
                else:
                    await message.reply_text(
                        part,
                        parse_mode='HTML'
                    )
        else:
            await message.reply_text(
                response,
                reply_to_message_id=message.message_id,
                parse_mode='HTML'
            )
        
        logger.info(f"Chat list displayed for admin {user_id} ({len(all_chats)} chats)")
        
    except Exception as e:
        logger.error(f"Error in /chats command: {e}")
        await message.reply_text(
            f"❌ Error: {str(e)}",
            reply_to_message_id=message.message_id
        )


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


async def check_and_make_autonomous_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if bot should make an autonomous comment and generate it.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message:
        return
    
    message = update.message
    chat_id = message.chat_id
    bot_user_id = context.bot.id
    
    try:
        # Check if should comment
        if not autonomous_commenter.should_comment(chat_id, bot_user_id):
            return
        
        # Additional AI check if enabled
        if config.yaml_config.autonomous_commenting.use_ai_decision:
            if not await autonomous_commenter.should_comment_ai_check(chat_id, bot_user_id, ai_provider):
                logger.info(f"AI decided not to comment in chat {chat_id}")
                return
        
        logger.info(f"Autonomous comment triggered for chat {chat_id}")
        
        # Generate comment
        comment = await autonomous_commenter.generate_comment(
            chat_id=chat_id,
            ai_provider=ai_provider,
            bot_user_id=bot_user_id
        )
        
        if not comment:
            logger.warning(f"Failed to generate autonomous comment for chat {chat_id}")
            return
        
        # Send comment (reply or standalone)
        if comment.reply_to_message_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text=comment.text,
                reply_to_message_id=comment.reply_to_message_id
            )
            logger.info(f"Sent autonomous reply to message {comment.reply_to_message_id} in chat {chat_id}")
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=comment.text
            )
            logger.info(f"Sent autonomous standalone comment in chat {chat_id}")
        
        # Mark that we commented
        autonomous_commenter.mark_commented(chat_id)
        
        # Record roast if applicable
        if comment.target_user_id and comment.comment_type == "roast":
            profile_manager.record_roast(
                target_user_id=comment.target_user_id,
                roast_topic=comment.comment_type,
                success=True
            )
        
    except Exception as e:
        logger.error(f"Error in autonomous commenting: {e}", exc_info=True)


async def check_and_add_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if bot should react to a message and add reaction.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message:
        return
    
    message = update.message
    chat_id = message.chat_id
    
    try:
        # Check if should react
        if not reaction_manager.should_react(chat_id):
            return
        
        logger.info(f"Autonomous reaction triggered for chat {chat_id}")
        
        # Choose appropriate reaction
        reaction = reaction_manager.choose_reaction(message.text)
        
        # Check if set_message_reaction is available (requires python-telegram-bot >= 20.0)
        if not hasattr(context.bot, 'set_message_reaction'):
            logger.warning("Reaction API not available in your python-telegram-bot version. Please upgrade to >= 20.0 for reaction support.")
            return
        
        # Add reaction to message using ReactionTypeEmoji
        from telegram import ReactionTypeEmoji
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=reaction)]
        )
        
        # Mark that we reacted
        reaction_manager.mark_reacted(chat_id)
        
        logger.info(f"Added reaction to message {message.message_id} in chat {chat_id}")
        
    except AttributeError as e:
        logger.error(f"Reaction API not supported: {e}. Upgrade python-telegram-bot to >= 20.0")
    except Exception as e:
        logger.error(f"Error adding reaction: {e}", exc_info=True)


async def _generate_ai_profile_summary(profile, language: str) -> str:
    """Generate comprehensive AI profile summary in target language.
    
    Args:
        profile: UserProfile object
        language: Target language ('ru' or 'en')
        
    Returns:
        str: Formatted profile summary
    """
    # Prepare profile data as JSON for AI
    import json
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
Формат Markdown. Начни с "👤 **{profile.first_name}**"."""
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
Markdown format. Start with "👤 **{profile.first_name}**"."""
    
    try:
        summary = await ai_provider.free_request(
            user_message=prompt,
            system_message="You are a skilled profiler. Create comprehensive, engaging profiles."
        )
        return summary
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        raise


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
