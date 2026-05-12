document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("reserva-form");
    if (!form) return;

    const alerta = document.getElementById("alerta-conflito");
    const dataInput = document.getElementById("id_data");
    const inicio = document.getElementById("id_horario_inicial");
    const fim = document.getElementById("id_horario_final");
    const recorrenteCheckbox = document.getElementById("id_recorrente_semanal");
    const recorrenciaWrap = document.getElementById("recorrencia-weeks-wrap");
    const applyInput = document.getElementById("id_apply_to_future");

    const hoje = new Date().toISOString().slice(0, 10);
    const apiUrl = form.dataset.apiUrl;
    const horariosUrl = form.dataset.horariosUrl;
    const reservaId = form.dataset.reservaId || "";
    const isEditing = form.dataset.isEditing === "1";
    const existingStart = form.dataset.existingStart || "";
    const existingEnd = form.dataset.existingEnd || "";

    let endOptionsCache = {};
    let suppressConflictCheck = false;

    if (dataInput) {
        dataInput.min = hoje;
    }

    function resetInvalidState() {
        [dataInput, inicio, fim].forEach((el) => {
            if (el) el.classList.remove("is-invalid");
        });
    }

    function mostrar(msg, tipo = "warning") {
        if (!alerta) return;
        alerta.className = `alert alert-${tipo}`;
        alerta.textContent = msg;
        alerta.classList.remove("d-none");
        resetInvalidState();
    }

    function limpar() {
        if (!alerta) return;
        alerta.classList.add("d-none");
        alerta.textContent = "";
        resetInvalidState();
    }

    function minutosFromTimeString(t) {
        const parts = String(t || "").split(":").map(Number);
        return parts[0] * 60 + parts[1];
    }

    function validarLocal() {
        if (!dataInput?.value || !inicio?.value || !fim?.value) return false;

        if (dataInput.value < hoje) {
            mostrar("Não é permitido reservar uma data passada.", "danger");
            dataInput.classList.add("is-invalid");
            return false;
        }

        const inicioMin = minutosFromTimeString(inicio.value);
        const fimMin = minutosFromTimeString(fim.value);

        if (fimMin <= inicioMin) {
            mostrar("O horário final deve ser maior que o horário inicial.", "danger");
            fim.classList.add("is-invalid");
            return false;
        }

        const duracao = fimMin - inicioMin;
        if (duracao < 30) {
            mostrar("A duração mínima da reserva é de 30 minutos.", "danger");
            inicio.classList.add("is-invalid");
            fim.classList.add("is-invalid");
            return false;
        }

        if (duracao % 30 !== 0) {
            mostrar("A duração da reserva deve ser múltipla de 30 minutos.", "danger");
            inicio.classList.add("is-invalid");
            fim.classList.add("is-invalid");
            return false;
        }

        return true;
    }

    function populateEndOptions(start) {
        if (!fim) return;
        fim.innerHTML = '<option value="">-- Selecione --</option>';
        if (!start) return;

        const ends = endOptionsCache[start] || [];
        ends.forEach((value) => {
            const opt = document.createElement("option");
            opt.value = value;
            opt.textContent = value;
            fim.appendChild(opt);
        });
    }

    async function carregarHorarios() {
        if (!inicio || !fim || !dataInput) return;

        inicio.innerHTML = '<option value="">-- Selecione --</option>';
        fim.innerHTML = '<option value="">-- Selecione --</option>';
        endOptionsCache = {};

        if (!dataInput.value) return;

        const url = new URL(horariosUrl, window.location.origin);
        url.searchParams.set("data", dataInput.value);
        if (reservaId) url.searchParams.set("reserva_id", reservaId);

        try {
            const resp = await fetch(url.toString(), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!resp.ok) return;

            const payload = await resp.json();
            const startSlots = payload.start_slots || [];
            endOptionsCache = payload.end_options || {};

            startSlots.forEach((slot) => {
                const opt = document.createElement("option");
                opt.value = slot;
                opt.textContent = slot;
                inicio.appendChild(opt);
            });

            if (isEditing && existingStart) {
                inicio.value = existingStart;
                populateEndOptions(existingStart);
                if (existingEnd) {
                    fim.value = existingEnd;
                }
            }
        } catch (e) {
            // silencioso: mantém o comportamento atual
        }
    }

    async function checarConflito() {
        if (suppressConflictCheck) return;
        if (!validarLocal()) return;

        const url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("data", dataInput.value);
        url.searchParams.set("horario_inicial", inicio.value);
        url.searchParams.set("horario_final", fim.value);
        if (reservaId) url.searchParams.set("reserva_id", reservaId);

        try {
            const resp = await fetch(url.toString(), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const payload = await resp.json();

            if (payload.conflito) {
                mostrar(payload.mensagem, "warning");
                dataInput.classList.add("is-invalid");
                inicio.classList.add("is-invalid");
                fim.classList.add("is-invalid");
            } else {
                limpar();
            }
        } catch (e) {
            limpar();
        }
    }

    function toggleRecorrencia() {
        if (!recorrenteCheckbox || !recorrenciaWrap) return;
        recorrenciaWrap.style.display = recorrenteCheckbox.checked ? "block" : "none";
    }

    if (recorrenteCheckbox) {
        recorrenteCheckbox.addEventListener("change", toggleRecorrencia);
        toggleRecorrencia();
    }

    if (dataInput) {
        dataInput.addEventListener("change", async function () {
            suppressConflictCheck = true;
            await carregarHorarios();
            suppressConflictCheck = false;
            limpar();
        });
    }

    if (inicio) {
        inicio.addEventListener("change", function () {
            populateEndOptions(inicio.value);
            if (fim && fim.options.length > 1) fim.selectedIndex = 1;
            checarConflito();
        });
    }

    if (fim) {
        fim.addEventListener("change", checarConflito);
    }

    if (dataInput?.value) {
        carregarHorarios();
    }

    form.addEventListener("submit", function (e) {
        if (!validarLocal()) {
            e.preventDefault();
            return;
        }

        if (isEditing && applyInput) {
            const proceedAll = confirm("Alterar todos os agendamentos futuros?");
            applyInput.value = proceedAll ? "1" : "0";
        }
    });
});

