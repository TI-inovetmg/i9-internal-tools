import pandas as pd
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from .task import task_sincronizar_protheus
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from engenharia.services.producao_service import ProducaoQueryService


from core.decorators import exige_permissao
from .models import EstruturaProduto


@login_required(login_url='/login/')
@exige_permissao(['engenharia'])
def extrai_estrutura_simples(request):
    """View Magra: Apenas lida com Request, Paginação e Response."""

    busca = request.GET.get('busca', '')

    # Delega o trabalho pesado para a Camada de Serviço
    arvore_projetos = ProducaoQueryService.construir_arvore_projetos(termo_busca=busca)

    # Paginação em Nível de Projeto (Paginamos as chaves do dicionário)
    lista_projetos = list(arvore_projetos.items())
    paginator = Paginator(lista_projetos, 1)  # 1 Projetos inteiros por página
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Reconstroi o dicionário apenas com a "fatia" da página atual
    projetos_paginados = dict(page_obj.object_list)

    context = {
        'dados_agrupados': projetos_paginados,
        'page_obj': page_obj,
        'busca': busca
    }

    return render(request, 'engenharia/extrai_estrutura_simples.html', context)


@login_required(login_url='/login/')
@exige_permissao(['engenharia'])
def exportar_estrutura_excel(request):
    """View Magra: Intermedia a requisição HTTP e o retorno do Excel."""

    # Capta o filtro de busca da URL, se o usuário estiver buscando algo específico
    busca = request.GET.get('busca', '')

    # Pede ao serviço o DataFrame pronto e limpo
    df = ProducaoQueryService.gerar_dataframe_exportacao(termo_busca=busca)

    # Configura a Resposta HTTP dizendo pro navegador que é um arquivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Acompanhamento_Producao_Engenharia.xlsx"'

    # Grava o DataFrame diretamente na resposta de memória (Sem sujar o disco)
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        if df.empty:
            # Se vier vazio, exporta uma planilha com aviso
            pd.DataFrame([{"Aviso": "Nenhum dado encontrado para os filtros aplicados."}]).to_excel(writer, index=False)
        else:
            df.to_excel(writer, index=False, sheet_name='Analise_Producao')

    return response



@login_required(login_url='/login/')
@exige_permissao(['engenharia'])
@require_POST
def atualizar_banco_estrutura(request):
    if cache.get('lock_sync_engenharia'):
        return JsonResponse({
            "status": "locked",
            "message": "Sincronização já em andamento."
        })

    cache.set('lock_sync_engenharia', True, timeout=600)

    # Dispara a task assíncrona
    task = task_sincronizar_protheus.delay()

    return JsonResponse({
        "status": "processing",
        "task_id": task.id,
        "message": "Sincronização iniciada em segundo plano."
    })
