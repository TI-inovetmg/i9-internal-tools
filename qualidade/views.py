from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import RNC
import json




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


@login_required(login_url='/login/')
@require_POST
def api_atualizar_rnc(request, rnc_id):
    """
    Recebe requisições AJAX do Tabulator para atualizar uma célula específica.
    """
    try:
        # Lê o JSON enviado pelo Tabulator no frontend
        dados = json.loads(request.body)
        campo = dados.get('campo')
        valor = dados.get('valor')

        # Busca a RNC no banco de dados
        rnc = get_object_or_404(RNC, id=rnc_id)

        # colunas do Tabulator podem ser editadas diretamente
        campos_permitidos = {
            'descricao': 'descricao',
            'correcao': 'correcao',
            'causas_principais': 'causas_principais',
            'acao_corretiva': 'acao_corretiva',
            'eficacia_texto': 'eficacia_texto',
            'justificativa_criticidade': 'justificativa_criticidade',
        }

        # Tratamento especial para o Enum de Status
        mapa_status = {
            'Não iniciada': 'NI', 'Em andamento': 'EA', 'Concluído': 'CO',
            'Fora dos trilhos': 'FT', 'Registro preliminar': 'PR', 'Cancelado': 'CA'
        }

        if campo == 'status' and valor in mapa_status:
            rnc.status = mapa_status[valor]
            rnc.save(update_fields=['status', 'atualizado_em'])
            return JsonResponse({'status': 'sucesso'})

        elif campo in campos_permitidos:
            campo_model = campos_permitidos[campo]
            setattr(rnc, campo_model, valor)
            rnc.save(update_fields=[campo_model, 'atualizado_em'])
            return JsonResponse({'status': 'sucesso'})

        else:
            return JsonResponse({'status': 'erro', 'mensagem': 'Campo não autorizado para edição inline.'}, status=403)

    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)
