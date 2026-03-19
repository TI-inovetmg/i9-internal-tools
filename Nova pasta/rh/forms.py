import os
from django import forms
from django.core.exceptions import ValidationError
from .models import Candidatura, Vaga, SolicitacaoVaga, PesquisaDemissional


class CandidaturaForm(forms.ModelForm):
    class Meta:
        model = Candidatura
        fields = ['nome_completo', 'email', 'telefone', 'linkedin', 'curriculo']
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'linkedin': forms.URLInput(attrs={'class': 'form-control'}),
            'curriculo': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        }

    def clean_curriculo(self):
        arquivo = self.cleaned_data.get('curriculo')

        if arquivo:
            tamanho_maximo = 5 * 1024 * 1024  # 5 MB
            if arquivo.size > tamanho_maximo:
                raise ValidationError('O arquivo excede o limite de 5MB.')

            extensao = os.path.splitext(arquivo.name)[1].lower()
            extensoes_permitidas = ['.pdf', '.doc', '.docx']

            if extensao not in extensoes_permitidas:
                raise ValidationError('Segurança: Envie apenas currículos em PDF ou Word.')

        return arquivo



class VagaForm(forms.ModelForm):
    class Meta:
        model = Vaga
        fields = ['titulo', 'setor', 'descricao', 'requisitos', 'ativa']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Analista de TI Sênior'}),
            'setor': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva o dia a dia da função, responsabilidades e desafios...'}),
            'requisitos': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ex: Superior completo, experiência com Python, Django, etc...'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})
        }

class SolicitacaoVagaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoVaga
        exclude = ['solicitante', 'data_solicitacao', 'status', 'observacoes_rh']

        widgets = {
            'data_prevista_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cargo_solicitante': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Ex: Gerente de Obras'}),
            'nome_vaga': forms.TextInput(attrs={'class': 'form-control'}),
            'quantidade_vagas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'departamento': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Select(attrs={'class': 'form-select'}),
            'nome_substituido': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Preencha apenas em caso de substituição'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'escolaridade': forms.Select(attrs={'class': 'form-select'}),
            'curso_area': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Ex: Engenharia Civil, Administração...'}),
            'descricao_atividades': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'conhecimentos_desejaveis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'atitudes_desejaveis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes_gerais': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_data_prevista_inicio(self):
        data = self.cleaned_data.get('data_prevista_inicio')
        if data:
            if data.weekday() != 0:
                raise ValidationError(
                    "A política da empresa exige que as admissões ocorram sempre em uma Segunda-feira. Por favor, ajuste a data.")
        return data

    def clean(self):
        cleaned_data = super().clean()
        motivo = cleaned_data.get('motivo')
        nome_substituido = cleaned_data.get('nome_substituido')

        if motivo and 'SUBST' in motivo:
            if not nome_substituido:
                self.add_error('nome_substituido',
                               'Como o motivo é substituição, é obrigatório informar o nome de quem está saindo.')

        return cleaned_data

class PesquisaDemissionalGeracaoForm(forms.ModelForm):
    """
    Formulario exclusivo para o RH gerar link da pesquisa
    """
    class Meta:
        model = PesquisaDemissional
        fields = ['ex_funcionario_nome', 'setor', 'tipo_demissao', 'periodo_saida', 'tempo_casa']
        widgets = {
            'periodo_saida': forms.TextInput(attrs={'placeholder': 'Ex: Março/2026'}),
            'tempo_casa': forms.TextInput(attrs={'placeholder': 'Ex: 2 anos e 3 meses'})
        }

class PesquisaDemissionalRespostaForm(forms.ModelForm):
    """
    Formulario publico para o ex-colaborador responder
    """
    class Meta:
        model = PesquisaDemissional
        fields = [
            'motivo_saida', 'diferente', 'nota_lideranca',
            'nota_oportunidade', 'nota_reconhecimento',
            'nota_clima', 'nota_recomendacao'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        escala_1_a_5 = ['nota_lideranca', 'nota_oportunidade', 'nota_reconhecimento', 'nota_clima']
        for field in escala_1_a_5:
            self.fields[field].widget = forms.NumberInput(attrs={'min': 1, 'max': 5, 'required': True})

        self.fields['nota_recomendacao'].widget = forms.NumberInput(attrs={'min': 0, 'max': 10, 'required': True})

        self.fields['diferente'].widget = forms.Textarea(attrs={'rows': 4})