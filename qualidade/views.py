import json
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import RNC, Local, Equipamento, RNCImagem, RNCEficaciaImagem
from .service import RNCService
from core.decorators import exige_permissao

from rest_framework.decorators import api_view
from rest_framework.response import Response
from . serializers import RNCSerializer

User = get_user_model()

@login_required(login_url='/login/')
def dashboard_qualidade(request):
    usuario_sgq = request.user.pode_acessar_modulo('qualidade')

    locais_ativos = Local.objects.filter(ativo= True)
    equipamento_ativos = Equipamento.objects.filter(ativo= True)

    usuarios_ativos = User.objects.filter(is_active=True).order_by('first_name')

    context = {
        'locais': locais_ativos,
        'equipamentos': equipamento_ativos,
        'usuarios': usuarios_ativos,
        'is_sgq': usuario_sgq
    }
    return render(request, 'qualidade/dashboard.html', context)


@login_required(login_url='/login/')
def api_listar_rncs(request):
    """
    Retorna a lista completa de RNCs em formato JSON, incluindo textos e mídias.
    """
    rncs = RNC.objects.select_related(
        'registrador', 'equipamento', 'local'
    ).prefetch_related(
        'responsaveis', 'imagens', 'eficacia_imagens'
    ).all().order_by('-id')

    data = []
    for rnc in rncs:
        nomes_responsaveis = ", ".join([resp.get_full_name() or resp.username for resp in rnc.responsaveis.all()])
        imagens_urls = [img.imagem.url for img in rnc.imagens.all() if img.imagem]
        imagens_eficacia_urls = [img.imagens_eficacia.url for img in rnc.eficacia_imagens.all() if img.imagens_eficacia]

        data.append({
            'id': rnc.id,
            'registrador': rnc.registrador.get_full_name() or rnc.registrador.username,
            'registrador_id': rnc.registrador.id if rnc.registrador else None,
            'data_abertura': rnc.data_abertura.strftime('%Y/%m/%d') if rnc.data_abertura else '',
            'projeto_cod': rnc.projeto_cod or '-',
            'elemento_rastreador': rnc.elemento_rastreador or '-',
            'detector': rnc.get_detector_display(),
            'categoria': rnc.get_categoria_display(),
            'origem': rnc.get_origem_display(),
            'criticidade': rnc.get_criticidade_display(),
            'status': rnc.get_status_display(),
            'equipamento': rnc.equipamento.nome if rnc.equipamento else 'N/A',
            'local': rnc.local.nome if rnc.local else '-',
            'responsaveis': nomes_responsaveis,
            'responsaveis_ids': [resp.id for resp in rnc.responsaveis.all()],
            'data_prevista_conclusao': rnc.data_prevista_conclusao.strftime('%Y/%m/%d') if rnc.data_prevista_conclusao else '',
            'data_encerramento': rnc.data_encerramento.strftime('%Y/%m/%d') if rnc.data_encerramento else '',
            'descricao': rnc.descricao or '',
            'correcao': rnc.correcao or '',
            'ishikawa_link': rnc.ishikawa_link or '',
            'causas_principais': rnc.causas_principais or '',
            'acao_corretiva': rnc.acao_corretiva or '',
            'eficacia_texto': rnc.eficacia_texto or '',
            'eficacia_pdf': rnc.eficacia_pdf.url if rnc.eficacia_pdf else '',
            'qtd_imagens': len(imagens_urls),
            'primeira_imagem_url': imagens_urls[0] if imagens_urls else '',
            'imagens_urls': imagens_urls,
            'eficacia_imagens_urls': imagens_eficacia_urls,
            'qtd_imagens_eficacia': len(imagens_eficacia_urls),
            'primeira_imagem_eficacia_url': imagens_eficacia_urls[0] if imagens_eficacia_urls else '',
            'status_code': rnc.status,
            'categoria_code': rnc.categoria,
            'origem_code': rnc.origem,
            'criticidade_code': rnc.criticidade,
            'detector_code': rnc.detector,
            'equipamento_id': rnc.equipamento.id if rnc.equipamento else '',
            'local_id': rnc.local.id if rnc.local else '',
        })

    return JsonResponse(data, safe=False)


@login_required(login_url='/login/')
@require_POST
@exige_permissao(['qualidade'])
def api_atualizar_rnc(request, rnc_id):
    try:
        dados = json.loads(request.body)
        campo = dados.get('campo')
        valor = dados.get('valor')

        campos_permitidos = [
            'projeto_cod',
            'elemento_rastreador',
            'detector',
            'categoria',
            'origem',
            'criticidade',
            'status',
            'equipamento',
            'local',
            'descricao',
            'correcao',
            'ishikawa_link',
            'causas_principais',
            'acao_corretiva',
            'eficacia_texto',
            'eficacia_pdf',
            'responsaveis',
            'data_encerramento',
            'data_previsao_conclusao',
            'versao',
            'registrador'
        ]

        # Se o utilizador tentar enviar um campo que não está na lista, bloqueamos com erro 403 (Forbidden)
        if campo not in campos_permitidos:
            return JsonResponse({'status': 'erro', 'mensagem': 'Edição deste campo não autorizada.'}, status=403)

        # Se passou na segurança, delegamos a inteligência para o Service
        RNCService.atualizar_rnc(rnc_id, campo, valor)
        return JsonResponse({'status': 'sucesso'})

    except RNC.DoesNotExist:
        return JsonResponse({'status': 'erro', 'mensagem': 'RNC não encontrada.'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'erro', 'mensagem': 'Dados inválidos.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)


@login_required(login_url='/login/')
@require_POST
def api_criar_rnc(request):
    try:
        dados = json.loads(request.body)

        local = get_object_or_404(Local, id=dados.get('local_id'))
        equipamento_id = dados.get('equipamento_id')
        equipamento = get_object_or_404(Equipamento, id=equipamento_id) if equipamento_id else None

        registrador_id = dados.get('registrador_id')
        registrador_obj = User.objects.get(id=registrador_id) if registrador_id else request.user

        nova_rnc = RNC.objects.create(
            registrador=registrador_obj,
            local=local,
            equipamento=equipamento,
            detector=dados.get('detector'),
            categoria=dados.get('categoria'),
            origem=dados.get('origem'),
            criticidade=dados.get('criticidade'),
            descricao=dados.get('descricao'),
            status = 'PR'
        )

        responsaveis_ids = dados.get('responsaveis', [])

        if responsaveis_ids:
            nova_rnc.responsaveis.set(responsaveis_ids)
            RNCService.notificar_nova_rnc(nova_rnc.id, responsaveis_ids)

        return JsonResponse({'status': 'sucesso', 'rnc_id': nova_rnc.id})

    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)


@login_required(login_url='/login/')
@api_view(['POST'])
def api_criar_rnc(request):
    dados = request.data.copy()
    dados['status'] = 'PR'
    dados['local'] = dados.get('local_id')
    if dados.get('equipamento_id'):
        dados['equipamento'] = dados.get('equipamento_id')
    dados['registrador'] = dados.get('registrador_id') or request.user.id
    dados['status'] = 'PR'
    serializer = RNCSerializer(data=dados)

    if serializer.is_valid():
        # O .save() aqui executa automaticamente o RNC.objects.create() por baixo dos panos!
        nova_rnc = serializer.save()
        responsaveis_ids = dados.get('responsaveis', [])
        if responsaveis_ids:
            nova_rnc.responsaveis.set(responsaveis_ids)
            RNCService.notificar_nova_rnc(nova_rnc.id, responsaveis_ids)
        return Response({'status': 'sucesso', 'rnc_id': nova_rnc.id})
    else:
        print(f"ERROS DE VALIDAÇÃO: {serializer.errors}")
        return Response({'status': 'erro', 'mensagem': serializer.errors}, status=400)


@login_required(login_url='/login/')
@api_view(['POST'])
@exige_permissao(['qualidade'])
def api_editar_rnc_avancado(request, rnc_id):
    rnc = get_object_or_404(RNC, id=rnc_id)

    # 2. Guardamos as datas antigas para a lógica de e-mail (Mantemos sua regra de negócio)
    data_antiga = rnc.data_encerramento
    data_previsao = rnc.data_prevista_conclusao

    # 3. A Mágica do DRF: O Serializer faz o parse das datas, valida as siglas (Choices) e os arquivos!
    # O "partial=True" diz ao DRF: "Atualize apenas os campos que vierem no request, não exija todos".
    serializer = RNCSerializer(instance=rnc, data=request.data, partial=True)

    if serializer.is_valid():
        # Se os dados estiverem perfeitos, salva no banco.
        rnc_atualizada = serializer.save()

        # ==========================================
        # SEU DESAFIO AQUI (Complete o código):
        # O Serializer já salvou os responsáveis, o Ishikawa, os status, categoria, datas e o PDF principal!
        # Mas você ainda precisa lidar com as tabelas filhas (Imagens extras e Imagens de Eficácia).
        # Como você extrairia os arquivos MÚLTIPLOS de request.FILES e salvaria nas tabelas
        # RNCImagem e RNCEficaciaImagem usando o objeto 'rnc_atualizada'?
        # DICA: No DRF, você não usa request.FILES, você pode usar request.FILES.getlist('imagens')
        # ==========================================

        imagens = request.FILES.getlist('imagens')
        for img in imagens:
            # Para cada arquivo, criamos uma nova linha na tabela RNCImagem
            RNCImagem.objects.create(rnc=rnc_atualizada, imagem=img)

        imagens_eficacia = request.FILES.getlist('imagens_eficacia')
        for img in imagens_eficacia:
            # Para cada arquivo, criamos uma nova linha na tabela RNCEficaciaImagem
            RNCEficaciaImagem.objects.create(rnc=rnc_atualizada, imagens_eficacia=img)

        # Gatilho de e-mails (Mantemos sua regra)
        if rnc_atualizada.data_encerramento and rnc_atualizada.data_encerramento != data_antiga:
            RNCService._notificar_data_encerramento(rnc_atualizada.id)

        if rnc_atualizada.data_prevista_conclusao and rnc_atualizada.data_prevista_conclusao != data_previsao:
            RNCService._notificar_data_previsao(rnc_atualizada.id)

        # O DRF usa 'Response' ao invés de 'JsonResponse'
        return Response({'status': 'sucesso'})
    else:
        # Se alguém mandar uma sigla errada ou data num formato bizarro, o DRF te diz EXATAMENTE o campo que falhou!
        return Response({'status': 'erro', 'mensagem': serializer.errors}, status=400)