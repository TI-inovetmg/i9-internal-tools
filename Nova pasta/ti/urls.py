from django.urls import path
from . import views

urlpatterns = [
    path('novo/', views.novo_chamado, name='novo_chamado'),
    path('ti-admin/', views.ti_admin, name='ti_admin'),
    path('dashboard', views.dashboard_ti, name='dashboard_ti'),
    path('atender/<int:pk>', views.atender_chamado, name='atender_chamado'),
    path('meus-chamados/', views.meus_chamados, name='meus_chamados'),
    path('meus-chamados/<int:pk>/', views.detalhe_meu_chamado, name='detalhe_meu_chamado'),
    path('usuarios/', views.gestao_usuarios, name='gestao_usuarios'),
    path('usuarios/novo/', views.form_usuario, name='novo_usuario'),
    path('usuarios/<int:pk>/editar/', views.form_usuario, name='editar_usuario'),
]