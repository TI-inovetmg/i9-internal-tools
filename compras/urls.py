from django.urls import path
from . import views

urlpatterns = [
    path('api/upload-dw/', views.api_upload_compras, name='api_upload_compras'),
]