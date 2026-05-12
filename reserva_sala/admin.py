from django.contrib import admin
from .models import ReservaSala
@admin.register(ReservaSala)
class ReservaSalaAdmin(admin.ModelAdmin):
    list_display = ("data", "horario_inicial", "horario_final", "usuario", "cancelada", "created_at")
    list_filter = ("cancelada", "data")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name", "descricao")
    ordering = ("-data", "horario_inicial")
    readonly_fields = ("created_at", "updated_at")
