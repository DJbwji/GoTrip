from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [path('admin/', admin.site.urls), path('', include('core.urls')),
    path('account/', include('users.urls')), path('excursions/', include('tours.urls')),
    path('trips/', include('trips.urls')), path('bookings/', include('bookings.urls')),
    path('messages/', include('messaging.urls')), path('moderation/', include('moderation.urls'))]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
