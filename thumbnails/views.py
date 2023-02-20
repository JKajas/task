from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import decorator_from_middleware
from rest_framework.generics import (
    DestroyAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from .middleware import DecodeBase64Middleware
from .models import Image, ImageLink, Thumbnail
from .permissions import (
    BinaryImagePermission,
    ImagePermission,
    ThumbnailPermission,
)
from .serializers import (
    CreateUpdateImageSerializer,
    ListImageSerializer,
    RetrieveImageSerializer,
    RetrieveLinkImageSerializer,
    RetrieveThumbnailSerializer,
)
from .utils import update_thumbnails_after_changes_decorator


class ImageCreateListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ListImageSerializer
        return CreateUpdateImageSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        for image in queryset:
            image.update_thumbnails()
        return super().list(request, *args, **kwargs)

    @decorator_from_middleware(DecodeBase64Middleware)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        serializer = ListImageSerializer(
            instance, context={"request": request}
        )
        return Response(data=serializer.data, status=201)


class RetrieveBaseView(RetrieveAPIView):
    def get_object(self):
        img = get_object_or_404(
            self.model_class, token=self.kwargs.get("token")
        )
        return img


class RetrieveUpdateDestroyImageView(
    RetrieveBaseView, UpdateAPIView, DestroyAPIView
):
    permission_classes = [IsAuthenticated, ImagePermission]
    model_class = Image

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RetrieveImageSerializer
        return CreateUpdateImageSerializer

    @update_thumbnails_after_changes_decorator
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # instance.update_thumbnails_after_changes()
        return FileResponse(instance.image)

    @decorator_from_middleware(DecodeBase64Middleware)
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @decorator_from_middleware(DecodeBase64Middleware)
    def patch(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class RetrieveDestroyThumbnailView(RetrieveBaseView, DestroyAPIView):
    permission_classes = [IsAuthenticated, ThumbnailPermission]
    model_class = Thumbnail
    serializer_class = RetrieveThumbnailSerializer

    @update_thumbnails_after_changes_decorator
    def retrieve(self, request, *args, **kwargs):
        return FileResponse(self.get_object().thumbnail)


class RetrieveBinaryImage(RetrieveBaseView):
    permission_classes = [IsAuthenticated, BinaryImagePermission]
    model_class = ImageLink

    @update_thumbnails_after_changes_decorator
    def retrieve(self, request, *args, **kwargs):
        image_link = self.get_object()
        if not image_link.is_valid():
            return Response(status=404)
        image = image_link.image
        return FileResponse(image.image)


class GenerateLinkToImageView(RetrieveBaseView):
    permission_classes = [IsAuthenticated, BinaryImagePermission]
    model_class = Image

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        image_link = instance.generate_image_link()
        serializer = RetrieveLinkImageSerializer(
            image_link, context={"request": request}
        )
        return Response(data=serializer.data)
