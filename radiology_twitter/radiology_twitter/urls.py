from django.contrib import admin
from django.urls import path
from twitter_client.views import (hashtagsEditor)

urlpatterns = [
    path('', hashtagsEditor),
    path('admin/', admin.site.urls),
]
