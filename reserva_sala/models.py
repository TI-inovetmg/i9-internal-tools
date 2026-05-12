from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import uuid
class ReservaSala(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas_sala",
        verbose_name="Usuário responsável"
    )
    data = models.DateField(verbose_name="Data")
    horario_inicial = models.TimeField(verbose_name="Horário inicial")
    horario_final = models.TimeField(verbose_name="Horário final")
    descricao = models.TextField(verbose_name="Descrição / Motivo")
    cancelada = models.BooleanField(default=False, verbose_name="Cancelada")
    # Recorrência semanal: quando marcada, a reserva poderá ser replicada para semanas seguintes
    recorrente_semanal = models.BooleanField(default=False, verbose_name="Repetir toda semana")
    recorrencia_semanal_weeks = models.PositiveIntegerField(default=12, verbose_name="Nº de semanas (inclui esta)", help_text="Quantidade de semanas para repetir (inclui a semana atual)")
    # Identificador de série para agrupar ocorrências de uma mesma recorrência
    serie = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "Reserva de Sala"
        verbose_name_plural = "Reservas de Sala"
        ordering = ["-data", "horario_inicial"]
    def __str__(self):
        return f"{self.data} | {self.horario_inicial} - {self.horario_final}"

    def get_editar_url(self):
        return reverse("reserva_sala_editar", args=[self.pk])

    def get_cancelar_url(self):
        return reverse("reserva_sala_cancelar", args=[self.pk])

    @classmethod
    def buscar_conflito(cls, data, horario_inicial, horario_final, exclude_pk=None):
        """Verifica se existe conflito de horários na mesma data."""
        if not data or not horario_inicial or not horario_final:
            return None
        conflitos = cls.objects.filter(data=data, cancelada=False)
        if exclude_pk:
            conflitos = conflitos.exclude(pk=exclude_pk)
        for reserva in conflitos:
            if horario_inicial < reserva.horario_final and horario_final > reserva.horario_inicial:
                return reserva
        return None
    def clean(self):
        erros = {}
        if not self.cancelada:
            if self.data and self.data < timezone.localdate():
                erros["data"] = "Não é permitido reservar uma data passada."
            if self.horario_inicial and self.horario_final and self.horario_final <= self.horario_inicial:
                erros["horario_final"] = "O horário final deve ser maior que o horário inicial."
            # Verifica incrementos de 30 minutos
            if self.horario_inicial and self.horario_inicial.minute % 30 != 0:
                erros["horario_inicial"] = "O horário inicial deve estar em incrementos de 30 minutos (ex.: 13:00, 13:30)."
            if self.horario_final and self.horario_final.minute % 30 != 0:
                erros["horario_final"] = "O horário final deve estar em incrementos de 30 minutos (ex.: 13:00, 13:30)."

            # Verifica duração mínima e múltipla de 30 minutos
            if self.horario_inicial and self.horario_final and self.horario_final > self.horario_inicial:
                duracao = (timedelta(hours=self.horario_final.hour, minutes=self.horario_final.minute) - timedelta(hours=self.horario_inicial.hour, minutes=self.horario_inicial.minute)).total_seconds() / 60
                if duracao < 30:
                    erros["__all__"] = "A duração mínima da reserva é de 30 minutos."
                elif duracao % 30 != 0:
                    erros["__all__"] = "A duração da reserva deve ser múltipla de 30 minutos."
            conflito = self.buscar_conflito(
                self.data,
                self.horario_inicial,
                self.horario_final,
                exclude_pk=self.pk,
            )
            if conflito:
                usuario_conflito = conflito.usuario.get_full_name() or conflito.usuario.username
                mensagem = (
                    f"Já existe uma reserva nesse horário: {conflito.data.strftime('%d/%m/%Y')} "
                    f"{conflito.horario_inicial.strftime('%H:%M')} às {conflito.horario_final.strftime('%H:%M')} "
                    f"por {usuario_conflito}. Evite sobreposição total ou parcial."
                )
                erros["__all__"] = mensagem
        if erros:
            raise ValidationError(erros)
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
