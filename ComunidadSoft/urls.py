from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Rutas de autenticación de Django (login, logout, reseteo de contraseña).
    # Usan por convención los templates de prode/templates/registration/.
    path('accounts/', include('django.contrib.auth.urls')),
    # Rutas de la aplicación del Prode.
    path('', include('prode.urls')),
]
