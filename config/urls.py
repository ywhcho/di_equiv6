from django.contrib import admin
from django.urls import include, path

from .views import about_view, board_view, home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', home_view, name='home'),
    path('equiv_ingr/', include('equiv_ingr.urls')),
    path('equiv_htname/', include('equiv_htname.urls')),
    path('board/', board_view, name='board'),
    path('about/', about_view, name='about'),
]
