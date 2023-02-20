import datetime
import secrets
from io import BytesIO

from django.contrib.auth.models import AbstractUser
from django.core import files
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from PIL import Image as Img


class Tier(models.Model):
    class Tiers(models.TextChoices):
        BASIC = "BASIC", "basic"
        PREMIUM = "PREMIUM", "premium"
        ENTERPRISE = "ENTERPRISE", "enterprise"

    tier = models.CharField(
        max_length=255, default=Tiers.BASIC, choices=Tiers.choices
    )
    original_image = models.BooleanField(default=False)

    def __str__(self):
        return self.tier


class Size(models.Model):
    tier = models.ManyToManyField(Tier, related_name="sizes")
    height = models.IntegerField()


class User(AbstractUser):
    tier = models.ForeignKey(
        Tier, on_delete=models.CASCADE, null=True, related_name="users"
    )
    img_link_duration = models.IntegerField(
        default=0,
        validators=[MaxValueValidator(30000), MinValueValidator(300)],
    )


class TokenMixin(models.Model):
    token = models.CharField(max_length=25, null=True, verbose_name="token")

    class Meta:
        abstract = True

    def generate_token(self):
        return secrets.token_urlsafe(16)

    def save_generated_token(self):
        self.token = self.generate_token()
        return self.save()


class Image(TokenMixin):
    class Formats:
        ALLOWED = {
            "png": "PNG",
            "jpg": "JPEG",
            "jpeg": "JPEG",
        }

    image = models.ImageField()
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="image"
    )

    def generate_image_link(self):
        image_link = ImageLink.objects.create(
            image=self,
            token=self.generate_token(),
            valid_until=(
                timezone.now()
                + datetime.timedelta(seconds=self.user.img_link_duration)
            ),
        )
        return image_link

    def check_thumbnails(self):
        tier_sizes_thn_set = set(
            [obj.height for obj in self.user.tier.sizes.all()]
        )
        created_sizes_thn_set = set(
            [thumbnail.height for thumbnail in self.thumbnails.all()]
        )
        to_delete = list(created_sizes_thn_set - tier_sizes_thn_set)
        to_create = list(tier_sizes_thn_set - created_sizes_thn_set)
        return to_create, to_delete

    def create_thumbnails(self, to_create):
        import sys

        if not to_create:
            return None
        thumbnails = []
        for height in to_create:
            format = self.image.url.split(".")[-1]
            img = Img.open(self.image)
            img.thumbnail([height, height])
            img_io = BytesIO()
            img.save(img_io, format=self.Formats.ALLOWED[format])
            thn = InMemoryUploadedFile(
                img_io,
                "thumbnail",
                "thumbnail.%s" % self.Formats.ALLOWED[format],
                self.Formats.ALLOWED[format],
                sys.getsizeof(img_io),
                None,
            )
            thumbnails.append(
                Thumbnail.objects.create(
                    image=self,
                    height=height,
                    token=self.generate_token(),
                    thumbnail=thn,
                )
            )
        return thumbnails

    def delete_thumbnails(self, to_delete):
        if not to_delete:
            return None
        return self.thumbnails.filter(height__in=to_delete).delete()

    def update_thumbnails_after_changes(self):
        to_create, to_delete = self.check_thumbnails()
        self.create_thumbnails(to_create)
        self.delete_thumbnails(to_delete)
        return None

    def update_thumbnails(self):
        self.thumbnails.all().delete()
        to_create, to_delete = self.check_thumbnails()
        thumbnails = self.create_thumbnails(to_create)
        return thumbnails


class Thumbnail(TokenMixin):
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="thumbnails"
    )
    height = models.IntegerField()
    thumbnail = models.ImageField()


class ImageLink(TokenMixin):
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="expiring_link"
    )

    def is_valid(self):
        if self.valid_until < timezone.now():
            self.delete()
            return False
        return True
