import base64

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile

from .utils import image_format_from_json


class DecodeBase64Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, view_args, view_func, request, view_kwargs):
        image = request[0].data.pop("image")
        if not image:
            return None

        if isinstance(image, list):
            image = image[0]

        if isinstance(image, InMemoryUploadedFile):
            request[0].data["image"]=image
            return None
        try:
            to_file = base64.b64decode(image)
        except OSError:
            return None

        format = image_format_from_json(image)
        if not format:
            return None

        image = ContentFile(to_file)
        image = InMemoryUploadedFile(
            image,
            "name",
            "image%s" % format[0],
            format[1],
            image.size,
            None,
        )
        request[0].data["image"] = image
        return None

