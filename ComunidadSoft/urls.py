from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    # 1. 🔑 COLOCAMOS TUS RUTAS PERSONALIZADAS ARRIBA DE TODO 
    # De esta forma Django las lee primero y se ve obligado a usar tus HTML
    path('accounts/login/', 
         auth_views.LoginView.as_view(template_name='registracion/login.html'), 
         name='login'),
    
    path('accounts/logout/', 
         auth_views.LogoutView.as_view(), 
         name='logout'),
    
    path('accounts/password_reset/', 
         auth_views.PasswordResetView.as_view(template_name='registracion/password_reset_form.html'), 
         name='password_reset'),
    
    path('accounts/password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='registracion/password_reset_done.html'), 
         name='password_reset_done'),
    
    path('accounts/reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='registracion/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    
    path('accounts/reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='registracion/password_reset_complete.html'), 
         name='password_reset_complete'),

    # 2. El panel de administración
    path('admin/', admin.site.urls), 
    
    # 3. Las rutas de la aplicación del Prode (las dejamos abajo)
    path('', include('prode.urls')),      
]