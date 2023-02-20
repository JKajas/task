from rest_framework.permissions import BasePermission

from .models import Tier, Thumbnail


class ThumbnailPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.image.user == request.user
    def has_permission(self, request, view):
        obj = Thumbnail.objects.filter(token=view.kwargs.get("token")).first()
        return obj.height in [size.height for size in request.user.tier.sizes.all()]


class ImagePermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
    def has_permission(self, request, view):
        if request.user.tier.original_image:
            return True

        return False

class BinaryImagePermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.image.user == request.user   
    def has_permission(self, request, view):
        return request.user.tier.tier == Tier.Tiers.ENTERPRISE
