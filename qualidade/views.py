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
    Retorna a lista completa de RNCs em formato JSON, incluindo textos e mídias.
    """
    # prefetch_related para otimizar a busca das fotos
    rncs = RNC.objects.select_related(
        'registrador', 'equipamento', 'local', 'tipo_nc'
    ).prefetch_related(
        'responsaveis', 'imagens'
    ).all().order_by('-id')

    data = []
    for rnc in rncs:
        nomes_responsaveis = ", ".join([resp.get_full_name() or resp.username for resp in rnc.responsaveis.all()])

        # Extrai os links das imagens vinculadas
        imagens_urls = [img.imagem.url for img in rnc.imagens.all() if img.imagem]

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
            'equipamento': rnc.equipamento.nome if rnc.equipamento else 'N/A',
            'local': rnc.local.nome if rnc.local else '-',
            'tipo_nc': rnc.tipo_nc.nome if rnc.tipo_nc else '-',
            'responsaveis': nomes_responsaveis,
            'data_prevista_conclusao': rnc.data_prevista_conclusao.strftime(
                '%d/%m/%Y') if rnc.data_prevista_conclusao else '',
            'data_encerramento': rnc.data_encerramento.strftime('%d/%m/%Y') if rnc.data_encerramento else '',

            'justificativa_criticidade': rnc.justificativa_criticidade or '',
            'descricao': rnc.descricao or '',
            'correcao': rnc.correcao or '',
            'ishikawa_link': rnc.ishikawa_link or '',
            'causas_principais': rnc.causas_principais or '',
            'acao_corretiva': rnc.acao_corretiva or '',
            'eficacia_texto': rnc.eficacia_texto or '',

            # Mídias
            'eficacia_pdf': rnc.eficacia_pdf.url if rnc.eficacia_pdf else '',
            'qtd_imagens': len(imagens_urls),
            'primeira_imagem_url': imagens_urls[0] if imagens_urls else '',
        })

    return JsonResponse(data, safe=False)