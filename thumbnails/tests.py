import base64
import json
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import (
    APIClient,
    APIRequestFactory,
    force_authenticate,
)

from thumbnails.validators import Validator
from thumbnails.views import (
    GenerateLinkToImageView,
    ImageCreateListView,
    RetrieveBinaryImage,
    RetrieveDestroyThumbnailView,
    RetrieveUpdateDestroyImageView,
)

from .middleware import DecodeBase64Middleware
from .models import Image, ImageLink, Size, Tier
from .serializers import (
    CreateUpdateImageSerializer,
    ListImageSerializer,
    RetrieveImageSerializer,
    RetrieveThumbnailSerializer,
)


class TestMixin(TestCase):

    factory = APIRequestFactory()

    def setUp(self):
        self.tier_basic = Tier.objects.create(tier=Tier.Tiers.BASIC)
        self.tier_premium = Tier.objects.create(
            tier=Tier.Tiers.PREMIUM, original_image=True
        )
        self.tier_enterprise = Tier.objects.create(
            tier=Tier.Tiers.ENTERPRISE, original_image=True
        )
        self.user = get_user_model().objects.create_user(
            username="test", password="password", email="test@test.pl"
        )
        self.user.img_link_duration = 300
        self.user.tier = self.tier_premium
        self.user.save()

        self.size_200 = Size.objects.create(height=200)
        self.size_200.tier.add(self.tier_basic)
        self.size_200.tier.add(self.tier_premium)
        self.size_200.tier.add(self.tier_enterprise)
        self.size_400 = Size.objects.create(height=400)
        self.size_400.tier.add(self.tier_premium)
        self.size_400.tier.add(self.tier_enterprise)
        self.image_content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAUA"
            + "AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO"
            + "9TXL0Y4OHwAAAABJRU5ErkJggg=="
        )
        self.image_data = SimpleUploadedFile(
            "image.png",
            self.image_content,
            content_type="image/png",
        )

        self.image = Image.objects.create(
            user=self.user,
            image=self.image_data,
            token=secrets.token_urlsafe(16),
        )


# test models
class TestImage(TestMixin):
    def test_generate_image_link(self):
        image_link = self.image.generate_image_link()
        self.assertEqual(isinstance(image_link, ImageLink), True)
        self.assertEqual(image_link.image, self.image)
        self.assertEqual(type(image_link.token) == str, True)

    def test_check_thumbnails_if_create(self):
        to_create, to_delete = self.image.check_thumbnails()
        self.assertEqual(len(to_delete), 0)
        self.assertEqual(len(to_create), len(self.user.tier.sizes.all()))

    def test_create_thumbnails(self):
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)
        self.assertEqual(len(thumbnails), 2)

    def test_delete_thumbnails(self):
        sizes_to_del = [200, 400]
        self.image.delete_thumbnails(sizes_to_del)
        self.assertEqual(len(self.image.thumbnails.all()), 0)

    def test_update_thumbnails(self):
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)

        image_content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAA"
            + "EAAAABCAQAAAC1HAwCAAAAC0lE"
            + "QVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image_data = SimpleUploadedFile(
            "image.png",
            image_content,
            content_type="image/png",
        )
        self.image.image = image_data
        thumbnails_updated = self.image.update_thumbnails()
        self.assertNotEqual(thumbnails == thumbnails_updated, True)

    def test_check_thumbnails_if_subscribction_has_changed(self):
        self.image.update_thumbnails_after_changes()
        self.assertEqual(len(self.image.thumbnails.all()), 2)

        self.user.tier = self.tier_basic
        self.user.save()
        self.assertEqual(self.user.tier, self.tier_basic)

        self.image.update_thumbnails_after_changes()
        self.assertEqual(len(self.image.thumbnails.all()), 1)


class TestImageLink(TestMixin):
    def test_image_link_generate(self):
        image_link = self.image.generate_image_link()
        self.assertEqual(isinstance(image_link, ImageLink), True)
        self.assertEqual(image_link.image, self.image)
        self.assertEqual(type(image_link.token) == str, True)

    def test_valid_image_link(self):

        image_link = self.image.generate_image_link()
        image_link.valid_until = timezone.now() - timedelta(minutes=20)
        self.assertNotEqual(image_link.is_valid(), True)


# # test serializers


class TestRetrieveThumbnailSerializer(TestMixin):
    def test_serializing_model(self):
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)
        request = self.factory.get("/")
        request.user = self.user
        serializer = RetrieveThumbnailSerializer(
            thumbnails[0], context={"request": request}
        )
        serializer_index = list(serializer.data)[0]
        # check if serializer represents height as key
        self.assertEqual(serializer_index, 200)
        self.assertEqual(
            serializer.data[serializer_index],
            f"http://testserver/users/thumbnail/{thumbnails[0].token}",
        )

    def test_get_url_with_right_permission(self):
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)
        request = self.factory.get("/")
        request.user = self.user
        serializer = RetrieveThumbnailSerializer(
            thumbnails[0], context={"request": request}
        )
        serializer_index = list(serializer.data)[0]
        self.assertEqual(serializer_index, 200)
        self.assertEqual(self.user.tier, self.tier_premium)

    def test_get_url_with_wrong_permission(self):
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)
        request = self.factory.get("/")
        self.user.tier = self.tier_basic
        request.user = self.user
        serializer = RetrieveThumbnailSerializer(
            thumbnails[1], context={"request": request}
        )
        self.assertNotEqual(serializer.data, None)
        self.assertNotEqual(self.user.tier, self.tier_premium)


class TestRetrieveImageSerializer(TestMixin):
    def test_serializing_model(self):
        self.image.save_generated_token()
        request = self.factory.get("/")
        request.user = self.user
        serializer = RetrieveImageSerializer(
            self.image, context={"request": request}
        )
        self.assertEqual(
            serializer.data["url"],
            f"http://testserver/users/image/{self.image.token}",
        )


class TestListImageSerializer(TestMixin):
    def test_serializing_model_with_tier_basic(self):
        self.image.save_generated_token()
        image_link = self.image.generate_image_link()
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)
        request = self.factory.get("/")
        self.user.tier = self.tier_basic
        request.user = self.user
        serializer = ListImageSerializer(
            self.image, context={"request": request}
        )
        self.assertEqual(len(list(serializer.data)), 1)
        self.assertEqual(
            list(serializer.data["thumbnails"][0])[0], thumbnails[0].height
        )

    def test_serializing_model_with_tier_premium(self):
        self.image.save_generated_token()
        image_link = self.image.generate_image_link()
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)
        request = self.factory.get("/")
        request.user = self.user
        serializer = ListImageSerializer(
            self.image, context={"request": request}
        )
        self.assertEqual(
            list(serializer.data["thumbnails"][0])[0], thumbnails[0].height
        )
        self.assertEqual(
            list(serializer.data["thumbnails"][1])[0], thumbnails[1].height
        )
        self.assertNotEqual(serializer.data["image"], None)
        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(len(serializer.data["thumbnails"]), 2)

    def test_serializing_model_with_tier_enterprise(self):
        self.image.save_generated_token()
        image_link = self.image.generate_image_link()
        to_create, to_delete = self.image.check_thumbnails()
        thumbnails = self.image.create_thumbnails(to_create)
        request = self.factory.get("/")
        self.user.tier = self.tier_enterprise
        request.user = self.user
        serializer = ListImageSerializer(
            self.image, context={"request": request}
        )
        self.assertEqual(len(serializer.data), 3)
        self.assertEqual(len(serializer.data["thumbnails"]), 2)
        self.assertEqual(
            list(serializer.data["thumbnails"][0])[0], thumbnails[0].height
        )
        self.assertEqual(
            list(serializer.data["thumbnails"][1])[0], thumbnails[1].height
        )
        self.assertNotEqual(serializer.data["image"], None)
        self.assertNotEqual(serializer.data["binary"], None)


class TestCreateUpdateSerializer(TestMixin):
    def test_create_image_model(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )
        request = self.factory.get("/")
        request.user = self.user
        serializer = CreateUpdateImageSerializer(
            data={"image": image}, context={"request": request}
        )
        serializer.is_valid()
        image = serializer.create(serializer.validated_data)
        self.assertNotEqual(image, None)
        self.assertEqual(len(image.thumbnails.all()), 2)

    def test_update_image_model(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )
        request = self.factory.get("/")
        request.user = self.user
        serializer = CreateUpdateImageSerializer(
            data={"image": self.image}, context={"request": request}
        )
        serializer.is_valid()
        image = serializer.update(self.image, serializer.validated_data)
        self.assertNotEqual(image.image, image)

    def test_validate_image(self):
        content = b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        image_data = SimpleUploadedFile(
            "image.gif",
            content,
            content_type="image/gif",
        )
        request = self.factory.get("/")
        request.user = self.user
        serializer = CreateUpdateImageSerializer(
            data={"image": image_data}, context={"request": request}
        )
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(
            serializer.errors["image"][0], Validator.WRONG_FORMAT.detail[0]
        )


# test middlewares
class TestBase64Middleware(TestMixin):
    def test_upload_base64_image(self):

        get_response = ImageCreateListView().as_view()
        request = self.factory.post(
            "/users/image/",
            json.dumps(
                {
                    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
                }
            ),
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        middleware = DecodeBase64Middleware(get_response)
        response = middleware(request)
        self.assertEqual(response.status_code, 201)

    def test_upload_form_data_image(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )

        get_response = ImageCreateListView().as_view()
        request = self.factory.post(
            "/users/image/",
            {
                "image": image,
            },
        )
        force_authenticate(request, user=self.user)
        middleware = DecodeBase64Middleware(get_response)
        response = middleware(request)
        self.assertEqual(response.status_code, 201)


# test create views
class TestImageCreateListView(TestMixin):
    def test_create_image(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )

        view = ImageCreateListView.as_view()
        request = self.factory.post(
            "/users/image/",
            {
                "image": image,
            },
        )
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.data, None)
        self.assertNotEqual(response.data["image"], None)
        self.assertEqual(len(response.data["thumbnails"]), 2)

    def test_list_with_updating_tier(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )

        view = ImageCreateListView.as_view()
        request = self.factory.post(
            "/users/image/",
            {
                "image": image,
            },
        )
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, 201)
        self.user.tier = self.tier_basic
        self.user.save()
        request = self.factory.get("/users/image/")
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertNotEqual(response.data, None)
        self.assertEqual(response.data[0].get("image"), None)
        self.assertEqual(len(response.data[0]["thumbnails"]), 1)


# view/behavior tests
class TestUploadAndRetrieveImage(TestMixin):
    def test_upload_and_retrieve_image(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(
            "/users/image/",
            {
                "image": image,
            },
        )
        self.assertEqual(response.status_code, 201)
        response = client.get(response.data["image"]["url"])
        self.assertEqual(response.status_code, 200)


class TestUploadAndRetrieveThumbnails(TestMixin):
    def test_upload_and_retrieve_thumbnail(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            "/users/image/",
            {
                "image": image,
            },
        )
        self.assertEqual(response.status_code, 201)
        thumbnail_url = response.data["thumbnails"][0][200]
        response = client.get(thumbnail_url)
        self.assertEqual(response.status_code, 200)


class TestUploadGenerateLinkAndRetrieveBinary(TestMixin):
    def test_generate_link_and_retrieve_binary(self):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "test_image.png",
            content,
            "image/png",
        )
        self.user.tier = self.tier_enterprise
        self.user.save()
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(
            "/users/image/",
            {
                "image": image,
            },
        )
        self.assertEqual(response.status_code, 201)
        image_url = response.data["image"]["url"]
        response = client.get(image_url + "/generate/")
        self.assertEqual(response.status_code, 200)
        binary_url = response.data["url"]
        response = client.get(binary_url)
        self.assertEqual(response.status_code, 200)
