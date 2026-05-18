from django import forms
from .models import Chamado
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        self._validar_uploads(result)
        return result

    def _validar_uploads(self, arquivos):
        if not arquivos:
            return

        if not isinstance(arquivos, (list, tuple)):
            arquivos = [arquivos]

        max_files = getattr(settings, 'TI_MAX_UPLOAD_FILES', 5)
        max_size = getattr(settings, 'TI_MAX_UPLOAD_SIZE', 5 * 1024 * 1024)
        allowed_types = getattr(settings, 'TI_ALLOWED_UPLOAD_CONTENT_TYPES', {'image/jpeg', 'image/png', 'image/webp'})

        if len(arquivos) > max_files:
            raise ValidationError(f'Limite de {max_files} anexos por chamado.')

        for arquivo in arquivos:
            if arquivo.size > max_size:
                raise ValidationError(f'O arquivo {arquivo.name} excede o limite de {max_size // (1024 * 1024)} MB.')

            content_type = getattr(arquivo, 'content_type', '')
            if content_type not in allowed_types:
                raise ValidationError(f'O arquivo {arquivo.name} nao esta em um formato permitido.')


class ChamadoForm(forms.ModelForm):
    imagens = MultipleFileField(
        required=False,
        label="Anexar Prints/Fotos (Você pode selecionar várias de uma vez)"
    )

    class Meta:
        model = Chamado
        fields = ['titulo', 'setor', 'categoria', 'prioridade', 'descricao']


class AtendimentoChamadoForm(forms.ModelForm):
    class Meta:
        model = Chamado
        fields = ['tecnico', 'status', 'prioridade', 'categoria', 'setor', 'solucao']
        widgets = {
            'solucao': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Descreva detalhadamente a solução técnica aplicada para resolver este chamado...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tecnicos = User.objects.filter(
            Q(is_active=True),
            Q(is_ti=True) | Q(is_diretoria=True) | Q(is_superuser=True),
        ).order_by('first_name', 'last_name', 'username')

        if self.instance and self.instance.tecnico_id:
            tecnicos = User.objects.filter(
                Q(pk=self.instance.tecnico_id) | Q(pk__in=tecnicos.values('pk'))
            ).distinct()

        self.fields['tecnico'].queryset = tecnicos
        self.fields['tecnico'].required = False
        self.fields['tecnico'].empty_label = 'Sem tecnico responsavel'

        if self.instance and not self.instance.validado_pelo_solicitante:
            opcoes_atuais = list(self.fields['status'].choices)
            self.fields['status'].choices = [opcao for opcao in opcoes_atuais if opcao[0] != 'CONCLUIDO']

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')

        if status == 'CONCLUIDO' and self.instance and not self.instance.validado_pelo_solicitante:
            self.add_error('status',
                           'OPERAÇÃO BLOQUEADA (ITIL): Apenas o usuário pode encerrar o chamado. Altere o status para "Resolvido".')

        return cleaned_data


User = get_user_model()


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label="Senha",
        help_text="Preencha apenas quando for criar um novo user ou alterar a senha atual."
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'teams_username',
                  'is_active', 'is_comercial', 'is_rh', 'is_ti', 'is_financeiro',
                  'is_engenharia', 'is_compras', 'is_pcp', 'is_diretoria', 'is_qualidade']

    def __init__(self, *args, **kwargs):
        # Captura o executor da requisição para blindar propriedades críticas do modelo
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Se o executor não for superuser, os privilégios departamentais são travados (Impede Injeção de Parâmetros)
        if current_user and not current_user.is_superuser:
            campos_privilegio = [
                'is_active', 'is_comercial', 'is_rh', 'is_ti', 'is_financeiro',
                'is_engenharia', 'is_compras', 'is_pcp', 'is_diretoria', 'is_qualidade'
            ]
            for campo in campos_privilegio:
                if campo in self.fields:
                    self.fields[campo].disabled = True

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')

        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
