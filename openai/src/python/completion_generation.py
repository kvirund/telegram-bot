import openai
import click
import sys
import json

@click.command()
@click.option("--api-key", "api_key")
@click.option("--organization", "organization")
@click.option("--output", "output")
@click.option("--request", "request")
@click.option("--user", "user")
def main(api_key, organization, output, request, user):
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"API key: {api_key}; Organization: {organization}; Result will be saved to {output};"
          f" Request: {request}; User: {user}")
    openai.organization = organization
    openai.api_key = api_key
    response = openai.Completion.create(engine="text-davinci-003", temperature=0.4, max_tokens=2048, prompt=request)
    with open(output + "/" + "response.json", "w") as f:
        json.dump(response, f)
    with open(output + ".txt", "wb") as f:
        f.write(response["choices"][0]["text"].encode("utf-8"))

if __name__ == "__main__":
    main()
