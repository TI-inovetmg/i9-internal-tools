from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import RNC


@login_required(login_url='/login/')
def dashboard_qualidade(request):
    return render(request, 'qualidade/dashboard.html')


@login_required(login_url='/login/')
def api_listar_rncs(request):
    """
    Retorna a lista completa de RNCs em formato JSON.
    Otimizado com select_related e prefetch_related para evitar N+1 queries.
    """
    rncs = RNC.objects.select_related(
        'registrador', 'equipamento', 'local', 'tipo_nc'
    ).prefetch_related(
        'responsaveis'
    ).all().order_by('-id')

    data = []
    for rnc in rncs:
        # Extrai a lista de responsáveis formatada como string (Ex: "João, Maria")
        nomes_responsaveis = ", ".join([resp.get_full_name() or resp.username for resp in rnc.responsaveis.all()])

        data.append({
            'id': rnc.id,
            'registrador': rnc.registrador.get_full_name() or rnc.registrador.username,
            'data_abertura': rnc.data_abertura.strftime('%d/%m/%Y') if rnc.data_abertura else '',
            'projeto_cod': rnc.projeto_cod or '-',
            'elemento_rastreador': rnc.elemento_rastreador or '-',
            'detector': rnc.get_detector_display(),
            'classificacao': rnc.get_classificacao_display(),
            'criticidade': rnc.get_criticidade_display(),
            'status': rnc.get_status_display(),

            # Tabelas de Domínio (trata casos onde equipamento possa ser nulo)
            'equipamento': rnc.equipamento.nome if rnc.equipamento else 'N/A',
            'local': rnc.local.nome if rnc.local else '-',
            'tipo_nc': rnc.tipo_nc.nome if rnc.tipo_nc else '-',

            'descricao': rnc.descricao,
            'responsaveis': nomes_responsaveis,
            'data_prevista_conclusao': rnc.data_prevista_conclusao.strftime(
                '%d/%m/%Y') if rnc.data_prevista_conclusao else '',
            'data_encerramento': rnc.data_encerramento.strftime('%d/%m/%Y') if rnc.data_encerramento else '',
        })

    # safe=False permite que o JsonResponse retorne uma lista (Array) em vez de um dicionário (Object)
    return JsonResponse(data, safe=False)