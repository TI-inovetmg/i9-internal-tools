from django import forms
from django.utils import timezone
# validation uses form.add_error; no direct ValidationError import needed
from datetime import timedelta
from .models import ReservaSala


class ReservaSalaForm(forms.ModelForm):
    class Meta:
        model = ReservaSala
        fields = ["data", "horario_inicial", "horario_final", "descricao", "recorrente_semanal", "recorrencia_semanal_weeks"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date", "class": "form-control shadow-sm"}),
            "horario_inicial": forms.TimeInput(attrs={"type": "time", "class": "form-control shadow-sm", "step": "1800"}),
            "horario_final": forms.TimeInput(attrs={"type": "time", "class": "form-control shadow-sm", "step": "1800"}),
            "descricao": forms.Textarea(attrs={
                "class": "form-control shadow-sm",
                "rows": 4,
                "placeholder": "Informe o motivo da reserva e detalhes importantes."
            }),
            "recorrente_semanal": forms.CheckboxInput(attrs={"class": "form-check-input ms-0"}),
            "recorrencia_semanal_weeks": forms.NumberInput(attrs={"class": "form-control shadow-sm", "min": 1, "max": 52}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data"].widget.attrs["min"] = timezone.localdate().isoformat()
        self.fields["data"].input_formats = ["%Y-%m-%d"]

    def clean(self):
        cleaned = super().clean()
        data = cleaned.get("data")
        inicio = cleaned.get("horario_inicial")
        fim = cleaned.get("horario_final")

        if not data or not inicio or not fim:
            return cleaned

        # Não permitir datas passadas
        if data < timezone.localdate():
            self.add_error("data", "Não é permitido reservar uma data passada.")

        # Verifica incrementos de 30 minutos (apenas minutos 00 ou 30)
        for campo, valor in (("horario_inicial", inicio), ("horario_final", fim)):
            if valor.minute % 30 != 0:
                self.add_error(campo, "Os horários devem estar em incrementos de 30 minutos (ex.: 13:00, 13:30).")

        # Horário final maior que inicial
        if fim <= inicio:
            self.add_error("horario_final", "O horário final deve ser maior que o horário inicial.")
            return cleaned

        # Duração mínima 30 minutos e múltiplo de 30
        duracao = (timedelta(hours=fim.hour, minutes=fim.minute) - timedelta(hours=inicio.hour, minutes=inicio.minute)).total_seconds() / 60
        if duracao < 30:
            self.add_error(None, "A duração mínima da reserva é de 30 minutos.")
        elif duracao % 30 != 0:
            self.add_error(None, "A duração da reserva deve ser múltipla de 30 minutos.")

        return cleaned

