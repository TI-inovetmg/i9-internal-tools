from django.core.mail import send_mail
from django.conf import settings
from .models import RNC


class RNCService:
    @staticmethod
    def atualizar_rnc(rnc_id, dados_atualizados, usuario_logado):
        rnc = RNC.objects.get(id=rnc_id)

        # Guarda estado antigo para comparação
        responsaveis_antigos = set(rnc.responsaveis.all())
        data_encerramento_antiga = rnc.data_encerramento

        # Lógica de atualização dos campos e incremento de versão para concorrência
        # ... (atualiza os campos baseados no dicionário dados_atualizados)
        rnc.versao += 1
        rnc.save()

        # Gatilho 1: Alteração de Data
        if 'data_encerramento' in dados_atualizados and rnc.data_encerramento != data_encerramento_antiga:
            RNCService._notificar_data_encerramento(rnc)

        # Gatilho 2: Alteração de Responsáveis (requer manipulação M2M)
        if 'responsaveis_ids' in dados_atualizados:
            rnc.responsaveis.set(dados_atualizados['responsaveis_ids'])
            responsaveis_novos = set(rnc.responsaveis.all())
            if responsaveis_antigos != responsaveis_novos:
                RNCService._notificar_mudanca_responsaveis(rnc, responsaveis_novos, responsaveis_antigos)

        return rnc

    @staticmethod
    def _notificar_data_encerramento(rnc):
        emails = [resp.email for resp in rnc.responsaveis.all() if resp.email]
        if emails:
            send_mail(
                subject=f'[SGQ] Alteração de Prazo - RNC #{rnc.id}',
                message=f'A RNC {rnc.id} teve sua data de encerramento alterada para {rnc.data_encerramento}.',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=emails,
                fail_silently=True
            )