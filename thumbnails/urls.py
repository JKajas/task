from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from . import views

urlpatterns = [
    path("image/", views.ImageCreateListView.as_view(), name="image_list"),
    path(
        "image/<str:token>",
        views.RetrieveUpdateDestroyImageView.as_view(),
        name="image_view",
    ),
    path(
        "thumbnail/<str:token>",
        views.RetrieveDestroyThumbnailView.as_view(),
        name="thumbnail_view",
    ),
    path(
        "binary/<str:token>",
        views.RetrieveBinaryImage.as_view(),
        name="binary_view",
    ),
    path("login", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "image/<str:token>/generate/",
        views.GenerateLinkToImageView.as_view(),
        name="generate_image",
    ),
]
