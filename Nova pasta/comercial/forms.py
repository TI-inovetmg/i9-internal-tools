from django import forms
from .models import STO


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)


class STOForm(forms.ModelForm):
    imagens = MultipleFileField(
        required=False,
        label="Anexar Fotos do Local / Equipamento"
    )

    solicitante_alteracao = forms.CharField(
        max_length=100,
        required=False,
        label="Quem solicitou esta alteração?",
        help_text="Obrigatório para registrar no Histórico de Revisões."
    )

    motivo_alteracao = forms.CharField(
        widget=forms.Textarea(
            attrs={'rows': 3, 'placeholder': 'Descreva detalhadamente o que você está alterando nesta STO...'}),
        required=False,
        label="O que foi alterado?",
        help_text="Descreva a alteração para fins de auditoria ISO 9001."
    )

    class Meta:
        model = STO
        fields = [
            'cliente', 'contato', 'cidade', 'email', 'atividade',
            'orc_obras', 'orc_engenharia', 'orc_equipamentos', 'orc_locacoes', 'orc_manutencoes', 'orc_outros',
            'local_atividade', 'data_prevista', 'produto', 'capacidade_fabrica', 'densidade', 'granulometria',
            'umidade',
            'tipo_frete', 'tipo_frete_outros',
            'eletrica_automacao', 'eletrica_automacao_outros',
            'civil', 'civil_outros',
            'montagem_campo', 'montagem_campo_outros',
            'equipamento_icamento', 'equipamento_icamento_outros',
            'pneumatica', 'pneumatica_outros',
            'despoeiramento', 'despoeiramento_outros',
            'instrumentos', 'instrumentos_outros',
            'destelhamento', 'destelhamento_outros',
            'jateamento_pintura', 'jateamento_pintura_outros',
            'informacoes_adicionais',
            'imagens',
            'risco_capacidade_financeira', 'risco_fabril', 'risco_qualidade', 'risco_requisitos_legais', 'risco_outros',
            'mkt_indicacao', 'mkt_linkedin', 'mkt_site', 'mkt_instagram', 'mkt_outros'
        ]

    def clean(self):
        cleaned_data = super().clean()

        if self.instance.pk:
            if not cleaned_data.get('solicitante_alteracao'):
                self.add_error('solicitante_alteracao', 'Informe quem solicitou a alteração.')
            if not cleaned_data.get('motivo_alteracao'):
                self.add_error('motivo_alteracao', 'Descreva o que foi alterado para o histórico.')

        return cleaned_data