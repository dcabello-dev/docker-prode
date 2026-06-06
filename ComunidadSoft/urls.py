from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # CAMBIÁ ESTA LÍNEA (quitá el .admin_url y poné .urls):
    path('admin/', admin.site.urls), 
    
    path('', include('prode.urls')),      
    path('accounts/', include('django.contrib.auth.urls')), 
]