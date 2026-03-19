from django.urls import path, include
from . import views

urlpatterns = [
    path('sto/nova/', views.criar_sto, name='criar_sto'),
    path('sto/lista/', views.listar_stos, name='listar_stos'),
    path('sto/exportar-csv/', views.exportar_stos_csv, name='exportar_stos_csv'),
    path('sto/<int:pk>/', views.ver_sto, name='ver_sto'),
    path('sto/<int:pk>/editar/', views.editar_sto, name='editar_sto'),
    path('sto/iso-versoes/', views.historico_versoes_iso, name='historico_versoes_iso'),
]