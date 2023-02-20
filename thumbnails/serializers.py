from collections import OrderedDict

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from .models import Image, ImageLink, Thumbnail, Tier
from .validators import Validator


class ModelSerializerWithToken(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        fields = ["url"]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.token:
            return request.build_absolute_uri(
                f"{reverse(f'{self.Meta.prefix}_view', kwargs={'token': obj.token})}"
            )

        return None


class RetrieveThumbnailSerializer(ModelSerializerWithToken):
    class Meta(ModelSerializerWithToken.Meta):
        model = Thumbnail
        prefix = "thumbnail"

    def get_url(self, obj):
        request = self.context.get("request")
        height_list = [size.height for size in request.user.tier.sizes.all()]
        if obj.height in height_list:
            return super().get_url(obj)

        return None

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict(
            [
                (instance.height, result[key])
                for key in result
                if result[key] is not None
            ]
        )


class RetrieveImageSerializer(ModelSerializerWithToken):
    class Meta(ModelSerializerWithToken.Meta):
        model = Image
        prefix = "image"


class RetrieveLinkImageSerializer(ModelSerializerWithToken):
    class Meta(ModelSerializerWithToken.Meta):
        model = ImageLink
        prefix = "binary"


class ListImageSerializer(serializers.ModelSerializer):
    binary = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    thumbnails = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ["image", "thumbnails", "binary"]

    def to_representation(self, instance):
        results = super().to_representation(instance)
        return OrderedDict(
            [
                (key, results[key])
                for key in results
                if results[key] is not None
            ]
        )

    def get_binary(self, obj):
        request = self.context.get("request")
        serializer = RetrieveLinkImageSerializer(
            obj.expiring_link.all(),
            context={"request": request},
            many=True,
        )
        if (
            request.user.tier.tier == Tier.Tiers.ENTERPRISE
            and len(list(serializer.data)) != 0
        ):
            return serializer.data

        return None

    def get_image(self, obj):
        request = self.context.get("request")
        serializer = RetrieveImageSerializer(obj, context={"request": request})
        if request.user.tier.original_image:
            return serializer.data
        return None

    def get_thumbnails(self, obj):
        request = self.context.get("request")
        serializer = RetrieveThumbnailSerializer(
            obj.thumbnails, many=True, context={"request": request}
        )
        return serializer.data


class CreateUpdateImageSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Image
        fields = [
            "image",
            "user",
        ]

    def create(self, validated_data):
        image = super().create(validated_data)
        image.save_generated_token()
        to_create, to_delete = image.check_thumbnails()
        image.create_thumbnails(to_create)
        return image

    def update(self, instance, validated_data):
        instance.thumbnails.all().delete()
        image = super().update(instance, validated_data)
        to_create, to_delete = image.check_thumbnails()
        image.create_thumbnails(to_create)
        return image

    def validate_image(self, value):
        if not value.content_type.endswith(
            tuple(Image.Formats.ALLOWED.keys())
        ):
            raise Validator.WRONG_FORMAT
        return value
