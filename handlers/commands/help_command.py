"""Help command handler for the Telegram bot."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.profile_manager import profile_manager


logger = logging.getLogger(__name__)


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
    config = get_config()
    is_admin = user_id in config.admin_user_ids

    # Build help message in selected language
    if language == 'ru':
        help_text = _build_russian_help(user_id, is_admin, config)
    else:
        help_text = _build_english_help(user_id, is_admin, config)

    await message.reply_text(
        help_text,
        reply_to_message_id=message.message_id,
        parse_mode='HTML'
    )
    logger.info(f"Sent {language} help to user {user_id} ({username})")


def _build_russian_help(user_id: int, is_admin: bool, config) -> str:
    """Build Russian help message.

    Args:
        user_id: User ID
        is_admin: Whether user is admin
        config: Bot configuration

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
    help_text += "/joke <тема> - Сгенерировать анекдот на тему\n"
    help_text += "/ask <вопрос> - Свободный запрос к ИИ\n"
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
        help_text += "🔐 <b>Команды администратора (только приватный чат):</b>\n"
        help_text += "/reload - Перезагрузить конфигурацию\n"
        help_text += "/comment <chat_id> - Принудительный комментарий\n"
        help_text += "/context [chat_id] - Очистить контекст чата\n"
        help_text += "/profile <пользователь> - Показать профиль\n"
        help_text += "/chats - Список всех активных чатов\n"
        help_text += "/setprompt [тип] [промпт] - Изменить системные промпты\n"
        help_text += "/saveprofiles - Сохранить все профили на диск\n\n"

        help_text += "<b>Примеры использования:</b>\n"
        help_text += "• /profile @username или /profile 123456789\n"
        help_text += "• /comment -1001234567890\n"
        help_text += "• /setprompt joke_generation Новый промпт\n\n"

    help_text += "ℹ️ <b>Возможности:</b>\n"
    help_text += "• Контекстные ответы\n"
    help_text += "• Профилирование пользователей\n"
    help_text += "• Автономные комментарии с ИИ\n"
    help_text += "• Поддержка нескольких языков\n"

    return help_text


def _build_english_help(user_id: int, is_admin: bool, config) -> str:
    """Build English help message.

    Args:
        user_id: User ID
        is_admin: Whether user is admin
        config: Bot configuration

    Returns:
        str: English help text
    """
    access_level = "Administrator" if is_admin else "User"

    help_text = "🤖 <b>Telegram Joke Bot Help</b>\n\n"
    help_text += f"👤 <b>Your Access Level:</b> {access_level}\n"
    help_text += f"🆔 <b>Your ID:</b> <code>{user_id}</code>\n\n"

    # Basic commands
    help_text += "📋 <b>Available Commands:</b>\n\n"
    help_text += "<b>Jokes & Conversation:</b>\n"
    help_text += "/joke - Generate joke from context\n"
    help_text += "/joke <topic> - Generate joke about topic\n"
    help_text += "/ask <question> - Free-form AI request\n"
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
        help_text += "/comment <chat_id> - Force comment\n"
        help_text += "/context [chat_id] - Clear chat context\n"
        help_text += "/profile <user> - Show user profile\n"
        help_text += "/chats - List all active chats\n"
        help_text += "/setprompt [type] [prompt] - Modify system prompts\n"
        help_text += "/saveprofiles - Force save all profiles\n\n"

        help_text += "<b>Usage Examples:</b>\n"
        help_text += "• /profile @username or /profile 123456789\n"
        help_text += "• /setprompt joke_generation New prompt text\n\n"

    help_text += "ℹ️ <b>Features:</b>\n"
    help_text += "• Context-aware responses\n"
    help_text += "• User profiling & tracking\n"
    help_text += "• AI-powered autonomous comments\n"
    help_text += "• Multi-language support\n"

    return help_text
