import openai
import click
import urllib.request

@click.command()
@click.option("--api-key", "api_key")
@click.option("--organization", "organization")
@click.option("--output", "output_filename")
@click.option("--request", "request")
@click.option("--user", "user")
def main(api_key, organization, output_filename, request, user):
    print(f"API key: {api_key}; Organization: {organization}; Image will be saved to {output_filename};"
          f" Request: {request}; User: {user}")

    openai.organization = organization
    openai.api_key = api_key
    response = openai.Image.create(prompt=request, n=1, size="1024x1024", user=user)
    urllib.request.urlretrieve(response["data"][0]["url"], output_filename)

if __name__ == "__main__":
    main()
