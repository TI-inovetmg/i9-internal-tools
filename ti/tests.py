from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch

from usuarios.models import CustomUser
from .forms import AtendimentoChamadoForm, ChamadoForm
from .models import Chamado
from .services import abrir_chamado, atualizar_atendimento


class ChamadoModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='solicitante',
            email='solicitante@example.com',
            password='senha-forte-123',
        )

    def test_data_fechamento_usa_datetime_quando_concluido(self):
        chamado = Chamado.objects.create(
            solicitante=self.user,
            titulo='Problema resolvido',
            descricao='Descricao objetiva',
            categoria='HARDWARE',
            prioridade='BAIXA',
            setor='T.I',
            status='RESOLVIDO',
            solucao='Solucao aplicada',
        )

        chamado.validado_pelo_solicitante = True
        chamado.status = 'CONCLUIDO'
        chamado.save()

        self.assertIsNotNone(chamado.data_fechamento)
        self.assertTrue(timezone.is_aware(chamado.data_fechamento))

    def test_limpa_data_fechamento_quando_reabre(self):
        chamado = Chamado.objects.create(
            solicitante=self.user,
            titulo='Problema reaberto',
            descricao='Descricao objetiva',
            categoria='HARDWARE',
            prioridade='BAIXA',
            setor='T.I',
            status='CONCLUIDO',
            solucao='Solucao aplicada',
            validado_pelo_solicitante=True,
        )

        chamado.status = 'EM_ATENDIMENTO'
        chamado.save()

        self.assertIsNone(chamado.data_fechamento)


class ChamadoUploadTests(TestCase):
    def valid_data(self):
        return {
            'titulo': 'Notebook sem rede',
            'descricao': 'Sem acesso a rede corporativa',
            'categoria': 'REDE',
            'prioridade': 'MEDIA',
            'setor': 'T.I',
        }

    @override_settings(TI_MAX_UPLOAD_FILES=1)
    def test_bloqueia_quantidade_excessiva_de_anexos(self):
        files = {
            'imagens': [
                SimpleUploadedFile('a.png', b'conteudo', content_type='image/png'),
                SimpleUploadedFile('b.png', b'conteudo', content_type='image/png'),
            ]
        }

        form = ChamadoForm(data=self.valid_data(), files=files)

        self.assertFalse(form.is_valid())
        self.assertIn('imagens', form.errors)

    def test_bloqueia_tipo_de_arquivo_nao_permitido(self):
        files = {
            'imagens': SimpleUploadedFile('payload.txt', b'conteudo', content_type='text/plain')
        }

        form = ChamadoForm(data=self.valid_data(), files=files)

        self.assertFalse(form.is_valid())
        self.assertIn('imagens', form.errors)


class ChamadoServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='abertura',
            email='abertura@example.com',
            password='senha-forte-123',
        )
        self.tecnico = CustomUser.objects.create_user(
            username='tecnico.um',
            email='tecnico.um@example.com',
            password='senha-forte-123',
            is_ti=True,
        )
        self.novo_tecnico = CustomUser.objects.create_user(
            username='tecnico.dois',
            email='tecnico.dois@example.com',
            password='senha-forte-123',
            is_ti=True,
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_abertura_cria_chamado_e_agenda_notificacao_pos_commit(self):
        form = ChamadoForm(data={
            'titulo': 'Erro no sistema',
            'descricao': 'Sistema nao abre',
            'categoria': 'SOFTWARE_CORPORATIVO',
            'prioridade': 'ALTA',
            'setor': 'T.I',
        })
        self.assertTrue(form.is_valid(), form.errors)

        with patch('ti.services.task_notificar_chamado.apply_async') as apply_async:
            with self.captureOnCommitCallbacks(execute=True):
                chamado = abrir_chamado(form=form, solicitante=self.user)

        self.assertEqual(chamado.solicitante, self.user)
        self.assertEqual(Chamado.objects.count(), 1)
        apply_async.assert_called_once_with(args=[chamado.id, 'ABERTURA'], countdown=5)

    def test_atendimento_permite_trocar_tecnico_sem_alterar_status(self):
        chamado = Chamado.objects.create(
            solicitante=self.user,
            tecnico=self.tecnico,
            titulo='Troca de tecnico',
            descricao='Chamado em atendimento',
            categoria='HARDWARE',
            prioridade='MEDIA',
            setor='T.I',
            status='EM_ATENDIMENTO',
        )
        form = AtendimentoChamadoForm(data={
            'tecnico': self.novo_tecnico.pk,
            'status': 'EM_ATENDIMENTO',
            'prioridade': 'MEDIA',
            'categoria': 'HARDWARE',
            'setor': 'T.I',
            'solucao': '',
        }, instance=chamado)
        self.assertTrue(form.is_valid(), form.errors)

        with patch('ti.services.task_notificar_chamado.delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                atualizado = atualizar_atendimento(form=form)

        self.assertEqual(atualizado.tecnico, self.novo_tecnico)
        delay.assert_called_once_with(chamado.id, 'ATRIBUIDO')

    def test_atendimento_com_mudanca_de_status_prioriza_notificacao_de_status(self):
        chamado = Chamado.objects.create(
            solicitante=self.user,
            tecnico=self.tecnico,
            titulo='Resolucao com troca',
            descricao='Chamado em atendimento',
            categoria='HARDWARE',
            prioridade='MEDIA',
            setor='T.I',
            status='EM_ATENDIMENTO',
        )
        form = AtendimentoChamadoForm(data={
            'tecnico': self.novo_tecnico.pk,
            'status': 'RESOLVIDO',
            'prioridade': 'MEDIA',
            'categoria': 'HARDWARE',
            'setor': 'T.I',
            'solucao': 'Equipamento substituido',
        }, instance=chamado)
        self.assertTrue(form.is_valid(), form.errors)

        with patch('ti.services.task_notificar_chamado.delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                atualizado = atualizar_atendimento(form=form)

        self.assertEqual(atualizado.tecnico, self.novo_tecnico)
        delay.assert_called_once_with(chamado.id, 'RESOLVIDO')
