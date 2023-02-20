from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from thumbnails.models import Tier


class Command(BaseCommand):
    def handle(self, *args, **options):
        admin = get_user_model().objects.create_superuser(
            email="test@test.pl", username="test", password="Test123"
        )
        admin.img_link_duration = 300
        admin.tier = Tier.objects.get(pk=3)
        admin.save()
        self.stdout.write(
            self.style.SUCCESS('Created admin "%s"' % admin.username)
        )
