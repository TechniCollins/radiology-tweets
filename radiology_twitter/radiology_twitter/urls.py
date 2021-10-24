from django.contrib import admin
from django.urls import path
from twitter_client.views import (hashtagsEditor, fullArchive, exportData)

urlpatterns = [
    path('', hashtagsEditor),
    path('full-archive-search/', fullArchive, name='full-archive-search'),
    path('export-data', exportData, name='export-data'),
    path('admin/', admin.site.urls),
]
