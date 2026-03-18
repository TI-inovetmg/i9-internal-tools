from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_qualidade, name='dashboard_qualidade'),
    path('api/rncs/', views.api_listar_rncs, name='api_listar_rncs'),
]