package com.homesoft.kvirundbot;

import com.pengrad.telegrambot.TelegramBot;
import com.pengrad.telegrambot.request.GetMe;
import com.pengrad.telegrambot.response.GetMeResponse;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import picocli.CommandLine;

import java.util.concurrent.Callable;

@CommandLine.Command
public class KvirundBot implements Callable<Integer> {
    final static Logger log = LogManager.getLogger();

    private TelegramBot bot;

    @CommandLine.Option(names = {"--api-key"})
    private String apiKey;

    @CommandLine.Option(names = "--organization")
    private String organization;

    @CommandLine.Option(names = "--token")
    private String token;

    public static void main(String[] args) {
        final int exitStatus = new CommandLine(new KvirundBot()).execute(args);
        System.exit(exitStatus);
    }

    @SuppressWarnings("unused")
    public Integer call() {
        try {
            log.info("Starting KvirundBot with token {}", token);

            this.bot = new TelegramBot(token);
            final GetMeResponse me = getMe();
            start(me);

            log.info("Username: {}", me.user());

            //noinspection InfiniteLoopStatement
            while (true) {
                //noinspection BusyWait
                Thread.sleep(Long.MAX_VALUE);
            }
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        } finally {
            stop();
        }
    }

    public GetMeResponse getMe() {
        log.trace("Executing getMe request.");

        final GetMe request = new GetMe();

        return bot.execute(request);
    }

    public void start(GetMeResponse me) {
        bot.setUpdatesListener(KBUpdatesListener.builder()
                .bot(bot)
                .apiKey(apiKey)
                .organization(organization)
                .me(me)
                .build());
    }

    public void stop() {
        bot.removeGetUpdatesListener();
    }
}
