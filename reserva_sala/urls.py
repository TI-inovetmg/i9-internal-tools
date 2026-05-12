from django.urls import path
from . import views
urlpatterns = [
    path("", views.reservas_sala_dashboard, name="reservas_sala_dashboard"),
    path("nova/", views.reserva_sala_nova, name="reserva_sala_nova"),
    path("<int:pk>/editar/", views.reserva_sala_editar, name="reserva_sala_editar"),
    path("<int:pk>/cancelar/", views.reserva_sala_cancelar, name="reserva_sala_cancelar"),
    path("api/conflito/", views.api_verificar_conflito_reserva, name="api_verificar_conflito_reserva"),
    path("api/horarios/", views.api_horarios_disponiveis, name="api_horarios_disponiveis"),
]
