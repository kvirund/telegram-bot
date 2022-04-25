package com.homesoft.kvirundbot;

import com.pengrad.telegrambot.TelegramBot;
import com.pengrad.telegrambot.request.GetMe;
import com.pengrad.telegrambot.response.GetMeResponse;
import lombok.Builder;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class KvirundBot {
    final static Logger log = LogManager.getLogger();

    final private TelegramBot bot;

    @Builder
    public KvirundBot(String token) {
        this.bot = new TelegramBot(token);
    }

    public GetMeResponse getMe() {
        log.trace("Executing getMe request.");

        final GetMe request = new GetMe();

        return bot.execute(request);
    }

    public void start() {
        bot.setUpdatesListener(KBUpdatesListener.builder().bot(bot).build());
    }

    public void stop() {
        bot.removeGetUpdatesListener();
    }

    public static void main(String[] args) {
        if (1 > args.length) {
            log.error("Usage: kvirund-bot <token>");
            return;
        }

        final KvirundBot bot = KvirundBot.builder().token(args[0]).build();

        log.info("Starting KvirundBot");
        bot.start();

        final GetMeResponse me = bot.getMe();
        log.info("Username: {}", me.user());
    }
}
