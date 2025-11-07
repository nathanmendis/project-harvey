from django.contrib import admin
from django.urls import path, include
from django.conf import settings               # <-- ADD THIS IMPORT
from django.conf.urls.static import static     # <-- ADD THIS IMPORT

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path('panel/', include('adminpanel.urls')),
]

# --- ADD THIS BLOCK AT THE END ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)