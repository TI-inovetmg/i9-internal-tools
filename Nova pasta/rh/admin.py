from django.contrib import admin
from .models import Vaga, Candidatura

@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'setor', 'ativa', 'data_criacao')
    list_filter = ('ativa', 'setor')
    search_fields = ('titulo',)

@admin.register(Candidatura)
class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'vaga', 'status', 'lgpd_consentimento', 'data_aplicacao')
    list_filter = ('status', 'vaga', 'lgpd_consentimento')
    search_fields = ('nome_completo', 'email')