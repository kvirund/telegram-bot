import openai
import click
import urllib.request
import json
import sys
import io

from PIL import Image

@click.command()
@click.option("--api-key", "api_key")
@click.option("--organization", "organization")
@click.option("--output", "output")
@click.option("--request", "request")
@click.option("--user", "user")
def main(api_key, organization, output, request, user):
    openai.organization = organization
    openai.api_key = api_key

    image = sys.stdin.buffer.read()
    png_image = get_png_image(image)

    response = openai.Image.create_variation(image=png_image, n=1, size="1024x1024", user=user)
    with open(output + "/" + "response.json", "w") as f:
        json.dump(response, f)
    urllib.request.urlretrieve(response["data"][0]["url"], output + ".jpeg")

def get_png_image(image):
    jpeg_bytes = io.BytesIO(image)
    pil_image = Image.open(jpeg_bytes)
    byte_array = io.BytesIO()
    pil_image.save(byte_array, format="PNG")
    return byte_array.getvalue()


if __name__ == "__main__":
    main()
