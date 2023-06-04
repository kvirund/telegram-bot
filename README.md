# telegram-bot

This is a bot for Telegram. It can say "Fuck off!" on russian and has integration with OpenAI API such as Chat GPT 3.5 (`text-davinci-003` model) and DALL-E.

Having account in OpenAI, start it with the following parameters:

```plain
Usage: <main class> [--api-key=<apiKey>] [--organization=<organization>]
                    [--token=<token>]
      --api-key=<apiKey>
      --organization=<organization>

      --token=<token>
```

Here `API key` as well as `organization` are taken from the OpenAPI account. The `token` is the bot token provided by the `@BotFather` bot in in the Telegram after executing the `/token` command.
