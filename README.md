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

To generate a nice log from the outputs, this command could be used:

```shell
for i in $(find ./ -type d -printf "%T@ %p\n"| tail -n +2 | sort -n | awk '{print $2}'); do
  if [ -f "${i}/response.json" ]; then
    perl -E 'say"="x80'
    echo "::: $(basename ${i}) :::"
    cat "${i}/request.txt"
    perl -E 'say;say "-" x 80'
    cat "${i}/response.json" | jq -r 'if .choices == null then "<picture?>" else .choices[0].text end'
  fi
done > summary.txt
```