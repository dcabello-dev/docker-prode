from django.urls import path

from . import views

urlpatterns = [
    path('', views.panel_prode, name='panel_prode'),
    path('ranking/', views.ranking_institucional, name='ranking'),
    path('acerca-de/', views.acerca_de, name='acerca_de'),
]