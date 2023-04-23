package com.homesoft.kvirundbot;

import com.homesoft.openai.OpenAI;
import com.pengrad.telegrambot.TelegramBot;
import com.pengrad.telegrambot.UpdatesListener;
import com.pengrad.telegrambot.model.*;
import com.pengrad.telegrambot.request.GetFile;
import com.pengrad.telegrambot.request.SendMessage;
import com.pengrad.telegrambot.request.SendPhoto;
import com.pengrad.telegrambot.response.GetFileResponse;
import com.pengrad.telegrambot.response.GetMeResponse;
import lombok.Builder;
import org.apache.commons.io.FileUtils;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.net.MalformedURLException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.Timestamp;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.stream.Collectors;

@Builder
public class KBUpdatesListener implements UpdatesListener {
    private static final String REQUESTS_LOG = "outputs/requests.log";

    private static final Logger log = LogManager.getLogger();

    private final TelegramBot bot;
    private final GetMeResponse me;

    private final String apiKey;
    private final String organization;

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

        boolean privateMessage = Chat.Type.Private == message.chat().type();
        boolean processed = false;
        if (null != message.text()) {
            final MessageEntity[] entities = message.entities();
            if (null != entities) {
                for (MessageEntity entity : entities) {
                    switch (entity.type()) {
                        case mention:
                            bot.execute(new SendMessage(message.chat().id(), "Пошёл нахуй!").replyToMessageId(message.messageId()));
                            processed = true;
                            break;

                        case bot_command:
                            final String request = Arrays.stream(message.text().split(" ")).skip(1).collect(Collectors.joining(" "));
                            processBotCommand(message.text().substring(entity.offset(), entity.length()), request, message);
                            processed = true;
                            break;

                        default:
                            log.warn("Unknown entity type '{}'", entity.type());
                    }
                }
            } else if (null != message.replyToMessage()) {
                final Message replyToMessage = message.replyToMessage();
                if (Objects.equals(replyToMessage.from().id(), me.user().id())) {
                    if (null != replyToMessage.photo()) {
                        final String request = message.text();
                        processBotCommand("/image", request, message);
                    } else if (null != replyToMessage.text()) {
                        final String request = message.text();
                        processBotCommand("/text", request, message);
                    }
                    processed = true;
                }
            }
        }

        if (privateMessage && !processed) {
            final String request = message.text();
            processBotCommand("/text", request, message);
        }
    }

    private void processBotCommand(String command, String request, Message message) {
        final String user = message.from().username();
        if ("/stats".equalsIgnoreCase(command)) {
            log.info("Processing '{}' command ({})", command, command.getBytes(StandardCharsets.UTF_8));
            bot.execute(new SendMessage(message.chat().id(), "42!"));
        } else if ("/image".equalsIgnoreCase(command)) {
            if (null != message.replyToMessage() && null != message.replyToMessage().photo()) {
                log.info("Got request '{}' from user '{}' associated with an image", request, user);

                final Message replyToMessage = message.replyToMessage();
                final byte[] photo = downloadPhoto(replyToMessage);

                executeOpenAIFeature(user,
                    message.chat().id(),
                    request,
                    openai -> openai.variateImage(photo),
                    result -> bot.execute(new SendPhoto(message.chat().id(), new File(result)).caption(request)));
            } else {
                log.info("Got request '{}' from user '{}' to generate an image", request, user);
                executeOpenAIFeature(user,
                        message.chat().id(),
                        request,
                        OpenAI::generateImage,
                        result -> bot.execute(new SendPhoto(message.chat().id(), new File(result)).caption(request)));
            }
        } else if ("/text".equalsIgnoreCase(command)) {
            if (null != message.replyToMessage() && null != message.replyToMessage().text()) {
                log.info("Got request '{}' from user '{}' associated with a text message", request, user);

                final Message replyToMessage = message.replyToMessage();

                executeOpenAIFeature(user,
                        message.chat().id(),
                        request,
                        openai -> openai.editText(replyToMessage.text()),
                        result -> {
                            try {
                                bot.execute(new SendMessage(message.chat().id(), Files.readString(Paths.get(result))));
                            } catch (IOException e) {
                                throw new RuntimeException(e);
                            }
                        });
            } else {
                executeOpenAIFeature(user,
                        message.chat().id(),
                        request,
                        OpenAI::generateTextCompletion,
                        result -> {
                            try {
                                bot.execute(new SendMessage(message.chat().id(), Files.readString(Paths.get(result))));
                            } catch (IOException e) {
                                throw new RuntimeException(e);
                            }
                        });
            }
        } else {
            log.warn("Unknown command {} ({})", command, command.getBytes(StandardCharsets.UTF_8));
            bot.execute(new SendMessage(message.chat().id(), "Я таких слов не ведаю."));
        }
    }

    private byte[] downloadPhoto(Message message) {
        final File temporaryDirectory = new File(System.getProperty("java.io.tmpdir"));
        final File temporaryFile;
        try {
            temporaryFile = File.createTempFile("photo", null, temporaryDirectory);
        } catch (IOException e) {
            log.error("Couldn't create temporary file", e);
            bot.execute(new SendMessage(message.chat().id(), "Что-то пошло не так."));
            return null;
        }

        final PhotoSize photoSize = message.photo()[3];
        final String fileId = photoSize.fileId();
        final GetFile getFile = new GetFile(fileId);
        final GetFileResponse response = bot.execute(getFile);
        try (InputStream is = new URL("https://api.telegram.org/file/bot" + bot.getToken() + "/" + response.file()
                .filePath()).openStream()) {
            FileUtils.copyInputStreamToFile(is, temporaryFile);
        } catch (MalformedURLException e) {
            log.error("Couldn't create URL", e);
            bot.execute(new SendMessage(message.chat().id(), "Что-то пошло не так."));
            return null;
        } catch (IOException e) {
            log.error("Couldn't download and save photo to a temporary file", e);
            bot.execute(new SendMessage(message.chat().id(), "Что-то пошло не так."));
            return null;
        }

        try {
            return FileUtils.readFileToByteArray(temporaryFile);
        } catch (IOException e) {
            log.error("Couldn't read photo from a temporary file", e);
            bot.execute(new SendMessage(message.chat().id(), "Что-то пошло не так."));
            return null;
        }
    }

    private void executeOpenAIFeature(String user, long chatId, String request, Function<OpenAI, String> generatorFunction, Consumer<String> resultConsumer) {
        final OpenAI openAI = OpenAI.builder()
                .apiKey(apiKey)
                .organization(organization)
                .user(user)
                .request(request)
                .build();
        try {
            final String resultFileName = generatorFunction.apply(openAI);
            resultConsumer.accept(resultFileName);
            logRequest(user, request, resultFileName);
        } catch (Exception e) {
            logRequest(user, request, "<failure>");
            bot.execute(new SendMessage(chatId, "Что-то пошло не так. :-("));
        }
    }

    private void logRequest(String user, String request, String result) {
        try (final FileWriter logFile = new FileWriter(REQUESTS_LOG, true)) {
            logFile.write(String.format("%s %s %s %s%n",
                    new Timestamp(System.currentTimeMillis()),
                    user,
                    result,
                    request));
        } catch (IOException e) {
            log.warn("Couldn't add log record to the file {}", REQUESTS_LOG);
        }
    }
}
