def image_format_from_json(image):
    if image.startswith("iVBORw0KGg"):
        format = (".png", "PNG")
    elif image.startswith("/9j/4"):
        format = (".jpeg", "JPEG")
    else:
        format = None
    return format


def update_thumbnails_after_changes_decorator(func):
    def wrapper(self, request, *args, **kwargs):
        try:
            image = self.get_object().image
            image.update_thumbnails_after_changes()
        except Exception:
            image = self.get_object()
            image.update_thumbnails_after_changes()
        return func(self, request, *args, **kwargs)

    return wrapper
