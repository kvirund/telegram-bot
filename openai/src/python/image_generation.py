import openai
import click
import urllib.request
import json

@click.command()
@click.option("--api-key", "api_key")
@click.option("--organization", "organization")
@click.option("--output", "output")
@click.option("--request", "request")
@click.option("--user", "user")
def main(api_key, organization, output, request, user):
    openai.organization = organization
    openai.api_key = api_key
    response = openai.Image.create(prompt=request, n=1, size="1024x1024", user=user)
    with open(output + "/" + "response.json", "w") as f:
        json.dump(response, f)
    urllib.request.urlretrieve(response["data"][0]["url"], output + ".jpeg")

if __name__ == "__main__":
    main()
