import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import date
from .forms import STOForm
from .models import STO, STOImagem, STORevisao, VersaoFormularioSTO


@login_required(login_url='/admin/login/')
def criar_sto(request):
    if not request.user.pode_acessar_modulo('comercial'):
        messages.error(request, "Acesso negado.")
        return redirect('home')

    if request.method == 'POST':
        form = STOForm(request.POST, request.FILES)
        if form.is_valid():
            sto = form.save(commit=False)
            sto.consultor = request.user

            hoje = date.today()
            versao_ativa = VersaoFormularioSTO.objects.filter(
                data_inicio__lte=hoje
            ).exclude(data_fim__lt=hoje).first()

            if versao_ativa:
                sto.versao_formulario = versao_ativa.versao
            else:
                sto.versao_formulario = "Versão Padrão (Sem Registro de Vigência)"

            sto.save()

            arquivos = request.FILES.getlist('imagens')
            for f in arquivos:
                STOImagem.objects.create(sto=sto, imagem=f)

            messages.success(request, 'Solicitação Técnica de Orçamento (STO) salva com sucesso!')
            return redirect('listar_stos')
    else:
        form = STOForm()

    return render(request, 'comercial/sto_form.html', {'form': form})


@login_required(login_url='/admin/login/')
def listar_stos(request):
    if not request.user.pode_acessar_modulo('comercial'):
        messages.error(request, "Acesso negado.")
        return redirect('home')

    stos = STO.objects.all().order_by('-data', '-id')
    return render(request, 'comercial/sto_lista.html', {'stos': stos})


@login_required(login_url='/admin/login/')
def exportar_stos_csv(request):
    if not request.user.pode_acessar_modulo('comercial'):
        return HttpResponse("Acesso negado", status=403)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_stos_i9tmg.csv"'
    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'ID', 'Data', 'Consultor', 'Cliente', 'Contato', 'Cidade',
        'Atividade', 'Capacidade (T/h)', 'Produto'
    ])

    stos = STO.objects.all().order_by('-id')
    for sto in stos:
        writer.writerow([
            sto.id,
            sto.data.strftime('%d/%m/%Y'),
            sto.consultor.get_full_name() or sto.consultor.username,
            sto.cliente,
            sto.contato,
            sto.cidade,
            sto.atividade,
            sto.capacidade_fabrica,
            sto.produto
        ])

    return response


@login_required(login_url='/admin/login/')
def ver_sto(request, pk):
    if not request.user.pode_acessar_modulo('comercial'):
        messages.error(request, "Acesso negado.")
        return redirect('home')

    sto = get_object_or_404(STO, pk=pk)
    return render(request, 'comercial/sto_detalhe.html', {'sto': sto})


@login_required(login_url='/admin/login/')
def editar_sto(request, pk):
    if not request.user.pode_acessar_modulo('comercial'):
        messages.error(request, "Acesso negado.")
        return redirect('home')

    sto = get_object_or_404(STO, pk=pk)

    usuarios_privilegiados = ['laura', 'gustavo']
    if request.user != sto.consultor and request.user.username.lower() not in usuarios_privilegiados and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para editar a STO de outro consultor.")
        return redirect('ver_sto', pk=sto.id)

    if request.method == 'POST':
        form = STOForm(request.POST, request.FILES, instance=sto)
        if form.is_valid():
            sto = form.save()


            solicitante_alt = form.cleaned_data.get('solicitante_alteracao')
            motivo_alt = form.cleaned_data.get('motivo_alteracao')

            if solicitante_alt and motivo_alt:
                STORevisao.objects.create(
                    sto=sto,
                    usuario_modificador=request.user,
                    solicitante=solicitante_alt,
                    motivo_alteracao=motivo_alt
                )

            arquivos = request.FILES.getlist('imagens')
            for f in arquivos:
                STOImagem.objects.create(sto=sto, imagem=f)

            messages.success(request, 'STO atualizada com sucesso! O log de revisão foi registrado.')
            return redirect('ver_sto', pk=sto.id)
    else:
        form = STOForm(instance=sto)

    return render(request, 'comercial/sto_form.html', {'form': form, 'sto': sto})


# --- NOVA VIEW PARA A TELA DE VERSÕES DA ISO 9001 ---
@login_required(login_url='/admin/login/')
def historico_versoes_iso(request):
    if not request.user.pode_acessar_modulo('comercial'):
        messages.error(request, "Acesso negado.")
        return redirect('home')

    versoes = VersaoFormularioSTO.objects.all().order_by('-data_inicio')
    return render(request, 'comercial/iso_versoes.html', {'versoes': versoes})