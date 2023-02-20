from django.contrib import admin
from django.urls import reverse

from .models import Image, ImageLink, Size, Thumbnail, Tier, User


@admin.action(description="Generate expiring link to image")
def generate_expiring_link(modeladmin, request, queryset):
    for image in queryset:
        image.generate_image_link()
    return None


class ImageAdmin(admin.ModelAdmin):
    readonly_fields = ["url"]
    fields = (
        "image",
        "user",
        "url",
    )

    actions = [generate_expiring_link]

    def save_model(self, request, obj, form, change) -> None:
        return obj.save_generated_token()

    def get_queryset(self, request):
        self.request = request
        return super().get_queryset(request)

    @admin.display(description="Url")
    def url(self, obj):
        return self.request.build_absolute_uri(
            f"{reverse(f'image_view', kwargs={'token': obj.token})}"
        )


class TierAdmin(admin.ModelAdmin):
    readonly_fields = ["size_list"]
    fields = (
        "tier",
        "size_list",
        "original_image"
    )
    @admin.display(description="Thumbnails sizes")
    def size_list(self, obj):
        return [size.height for size in obj.sizes.all()]


admin.site.register(ImageLink)
admin.site.register(Size)
admin.site.register(Thumbnail)
admin.site.register(User)
admin.site.register(Tier, TierAdmin)
admin.site.register(Image, ImageAdmin)
