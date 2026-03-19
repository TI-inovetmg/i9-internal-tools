from django.contrib import admin
from .models import STO, STOImagem, STORevisao, VersaoFormularioSTO

admin.site.register(STO)
admin.site.register(STOImagem)
admin.site.register(STORevisao)

@admin.register(VersaoFormularioSTO)
class VersaoFormularioSTOAdmin(admin.ModelAdmin):
    list_display = ('versao', 'data_inicio', 'data_fim')
    list_filter = ('data_inicio',)
    search_fields = ('versao',)
