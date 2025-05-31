from constants.exceptions import Exceptions
from helpers.index import download_image_to_byte_array
from models.index import ImageRequest, PromptRequest


def generate_image(req: PromptRequest, client):
    prompt = req.prompt
    owner = req.owner

    if not prompt or not isinstance(prompt, str):
        raise Exceptions.required_and_type_exception("Prompt")

    if not owner or not isinstance(owner, str):
        raise Exceptions.required_and_type_exception("Owner")

    try:
        response = client.images.generate(
            model="dall-e-3",
            user=owner,
            prompt=prompt,
        )
        image_url = response.data[0].url
        if not image_url:
            raise Exceptions.general_exception(500, "Failed to generate image")
        return {"image": image_url}

    except KeyError as e:
        raise Exceptions.required_and_type_exception(str(e))
    except Exception as e:
        raise e


def generation_variations(req: ImageRequest, client):
    image = req.image_url
    owner = req.owner

    if not image or not isinstance(image, str):
        raise Exceptions.required_and_type_exception("Image URL")

    if not owner or not isinstance(owner, str):
        raise Exceptions.required_and_type_exception("Owner")

    try:
        response = client.images.create_variation(
            model="dall-e-2",
            user=owner,
            image=download_image_to_byte_array(image),
        )
        image_url = response.data[0].url
        if not image_url:
            raise Exceptions.general_exception(
                500, "Failed to generate image variation"
            )
        return {"image": image_url}

    except KeyError as e:
        raise Exceptions.required_and_type_exception(str(e))
    except Exception as e:
        raise e
