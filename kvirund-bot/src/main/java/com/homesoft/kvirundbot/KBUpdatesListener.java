package com.homesoft.kvirundbot;

import com.pengrad.telegrambot.TelegramBot;
import com.pengrad.telegrambot.UpdatesListener;
import com.pengrad.telegrambot.model.*;
import com.pengrad.telegrambot.request.SendMessage;
import lombok.Builder;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.List;

@Builder
public class KBUpdatesListener implements UpdatesListener {
    final Logger log = LogManager.getLogger();

    final TelegramBot bot;

    @Override
    public int process(List<Update> updates) {
        log.info("Processing {} update(s).", updates.size());

        int result = UpdatesListener.CONFIRMED_UPDATES_NONE;
        for (Update update : updates) {
            if (null != update.message()) {
                processMessage(update.message());
            } else if (null != update.editedMessage()) {
                processMessage(update.editedMessage());
            } else if (null != update.myChatMember()) {
                processChatMemberUpdated(update.myChatMember());
            } else {
                log.warn("Unknown update {}", update);
            }
            result = update.updateId();
        }

        log.info("Last updated message: {}", result);
        return result;
    }

    private void processChatMemberUpdated(ChatMemberUpdated chatMember) {
        final String title = chatMember.chat().title();
        final Chat.Type type = chatMember.chat().type();
        final ChatMember.Status status = chatMember.newChatMember().status();
        switch (status) {
            case creator:
                log.info("We have become a creator of the {} '{}'",
                    Chat.Type.Private == type ? "private chat" : type.toString(),
                    title);
                break;

            case administrator:
                log.info("We have become an administrator of the {} '{}'",
                    Chat.Type.Private == type ? "private chat" : type.toString(),
                    title);
                break;

            case member:
                log.info("We have become a member of the {} '{}'",
                    Chat.Type.Private == type ? "private chat" : type.toString(),
                    title);
                break;

            case restricted:
                log.info("We have been restricted in the {} '{}'",
                    Chat.Type.Private == type ? "private chat" : type.toString(),
                    title);
                break;

            case left:
                log.info("We have left the {} '{}'",
                    Chat.Type.Private == type ? "private chat" : type.toString(),
                    title);
                break;

            case kicked:
                log.info("We have been kicked from the {} '{}'",
                    Chat.Type.Private == type ? "private chat" : type.toString(),
                    title);
                break;
        }
    }

    private void processMessage(Message message) {
        log.info("Processing message from {}: {}",
                message.from().username(),
                null == message.text() ? "<none>" : "'" + message.text() + "'");

        boolean mention = Chat.Type.Private == message.chat().type();
        if (null != message.text()) {
            final MessageEntity[] entities = message.entities();
            if (null != entities) {
                for (MessageEntity entity : entities) {
                    switch (entity.type()) {
                        case mention:
                            mention = true;
                            break;

                        case bot_command:
                            processBotCommand(message.text().substring(entity.offset(), entity.length()), message);
                            break;

                        default:
                            log.warn("Unknown entity type '{}'", entity.type());
                    }
                }
            }
        }

        if (mention) {
            bot.execute(new SendMessage(message.from().id(), "Пошёл нахуй!"));
        }
    }

    private void processBotCommand(String command, Message message) {
        if ("/stats".equalsIgnoreCase(command)) {
            log.info("Processing '{}' command", command);
            bot.execute(new SendMessage(message.chat().id(), "42!"));
        } else {
            log.warn("Unknown command");
            bot.execute(new SendMessage(message.chat().id(), "Я таких слов не ведаю."));
        }
    }
}
