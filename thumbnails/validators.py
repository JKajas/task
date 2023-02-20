from .models import Image
from rest_framework.validators import ValidationError


class Validator:
    WRONG_FORMAT = ValidationError(f"Image have to be one of the format: {tuple(Image.Formats.ALLOWED.keys())}")
