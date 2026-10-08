// =============================================================
// JB Ferramentas - Cadastro de cliente
// - Busca automática de endereço pelo CEP (API ViaCEP)
// - Máscaras de CPF/CNPJ, telefone e CEP
// - Validação de CPF/CNPJ (dígitos verificadores) e telefone
// Mensagens de erro ficam em elementos com aria-live, para que
// leitores de tela anunciem o problema (acessibilidade - WCAG).
// =============================================================

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("form_cadastro");
    const campoCodigo = document.getElementById("id_codigo");
    const campoTelefone = document.getElementById("id_telefone");
    const campoCep = document.getElementById("id_cep");
    const campoEndereco = document.getElementById("id_endereco");
    const campoNumero = document.getElementById("id_numero");
    const radiosTipo = document.querySelectorAll('input[name="tipo"]');

    // ---------- Utilitários ----------
    const somenteNumeros = (texto) => texto.replace(/\D/g, "");

    function mostrarErro(campo, mensagem) {
        const erro = document.getElementById(campo.id + "_erro");
        campo.setAttribute("aria-invalid", mensagem ? "true" : "false");
        if (erro) erro.textContent = mensagem || "";
    }

    function tipoPessoa() {
        const marcado = document.querySelector('input[name="tipo"]:checked');
        return marcado ? marcado.value : "pf";
    }

    // ---------- Validação de CPF ----------
    function cpfValido(cpf) {
        cpf = somenteNumeros(cpf);
        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

        for (let t = 9; t < 11; t++) {
            let soma = 0;
            for (let i = 0; i < t; i++) soma += Number(cpf[i]) * (t + 1 - i);
            const digito = ((soma * 10) % 11) % 10;
            if (digito !== Number(cpf[t])) return false;
        }
        return true;
    }

    // ---------- Validação de CNPJ ----------
    function cnpjValido(cnpj) {
        cnpj = somenteNumeros(cnpj);
        if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) return false;

        const calcular = (base) => {
            let peso = base.length - 7;
            let soma = 0;
            for (let i = 0; i < base.length; i++) {
                soma += Number(base[i]) * peso--;
                if (peso < 2) peso = 9;
            }
            const resto = soma % 11;
            return resto < 2 ? 0 : 11 - resto;
        };

        const d1 = calcular(cnpj.slice(0, 12));
        const d2 = calcular(cnpj.slice(0, 12) + d1);
        return d1 === Number(cnpj[12]) && d2 === Number(cnpj[13]);
    }

    // ---------- Máscaras ----------
    function mascaraCodigo(valor) {
        const n = somenteNumeros(valor);
        if (tipoPessoa() === "pj") {
            return n.slice(0, 14)
                .replace(/^(\d{2})(\d)/, "$1.$2")
                .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
                .replace(/\.(\d{3})(\d)/, ".$1/$2")
                .replace(/(\d{4})(\d)/, "$1-$2");
        }
        return n.slice(0, 11)
            .replace(/(\d{3})(\d)/, "$1.$2")
            .replace(/(\d{3})(\d)/, "$1.$2")
            .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    }

    function mascaraTelefone(valor) {
        const n = somenteNumeros(valor).slice(0, 11);
        if (n.length <= 10) {
            return n.replace(/^(\d{2})(\d)/, "($1) $2").replace(/(\d{4})(\d)/, "$1-$2");
        }
        return n.replace(/^(\d{2})(\d)/, "($1) $2").replace(/(\d{5})(\d)/, "$1-$2");
    }

    function mascaraCep(valor) {
        return somenteNumeros(valor).slice(0, 8).replace(/^(\d{5})(\d)/, "$1-$2");
    }

    // ---------- Validações por campo ----------
    function validarCodigo() {
        const pj = tipoPessoa() === "pj";
        const ok = pj ? cnpjValido(campoCodigo.value) : cpfValido(campoCodigo.value);
        mostrarErro(campoCodigo, ok ? "" : (pj ? "CNPJ inválido." : "CPF inválido."));
        return ok;
    }

    function validarTelefone() {
        const tamanho = somenteNumeros(campoTelefone.value).length;
        const ok = tamanho === 10 || tamanho === 11;
        mostrarErro(campoTelefone, ok ? "" : "Informe o telefone com DDD.");
        return ok;
    }

    // ---------- Busca de CEP (ViaCEP) ----------
    async function buscarCep() {
        const cep = somenteNumeros(campoCep.value);
        if (cep.length === 0) {
            mostrarErro(campoCep, "");
            return;
        }
        if (cep.length !== 8) {
            mostrarErro(campoCep, "O CEP deve ter 8 dígitos.");
            return;
        }

        mostrarErro(campoCep, "");
        const status = document.getElementById("id_cep_status");
        status.textContent = "Buscando endereço...";

        try {
            const resposta = await fetch("https://viacep.com.br/ws/" + cep + "/json/");
            const dados = await resposta.json();

            if (dados.erro) {
                status.textContent = "";
                mostrarErro(campoCep, "CEP não encontrado. Preencha o endereço manualmente.");
                return;
            }

            const partes = [dados.logradouro, dados.bairro].filter(Boolean);
            campoEndereco.value = partes.join(", ") + " - " + dados.localidade + "/" + dados.uf;
            status.textContent = "Endereço encontrado. Confira e informe o número.";
            campoNumero.focus();
        } catch (e) {
            status.textContent = "";
            mostrarErro(campoCep, "Não foi possível consultar o CEP agora. Preencha o endereço manualmente.");
        }
    }

    // ---------- Eventos ----------
    campoCodigo.addEventListener("input", () => {
        campoCodigo.value = mascaraCodigo(campoCodigo.value);
    });
    campoCodigo.addEventListener("blur", validarCodigo);

    radiosTipo.forEach((radio) => radio.addEventListener("change", () => {
        campoCodigo.placeholder = tipoPessoa() === "pj" ? "00.000.000/0000-00" : "000.000.000-00";
        campoCodigo.value = mascaraCodigo(campoCodigo.value);
        if (campoCodigo.value) validarCodigo();
    }));

    campoTelefone.addEventListener("input", () => {
        campoTelefone.value = mascaraTelefone(campoTelefone.value);
    });
    campoTelefone.addEventListener("blur", validarTelefone);

    campoCep.addEventListener("input", () => {
        campoCep.value = mascaraCep(campoCep.value);
        if (somenteNumeros(campoCep.value).length === 8) buscarCep();
    });
    campoCep.addEventListener("blur", buscarCep);

    form.addEventListener("submit", (evento) => {
        const codigoOk = validarCodigo();
        const telefoneOk = validarTelefone();

        if (!codigoOk || !telefoneOk) {
            evento.preventDefault();
            (codigoOk ? campoTelefone : campoCodigo).focus();
            return;
        }

        // O banco guarda o endereço em um único campo: junta o número
        // (e o CEP, se informado) antes de enviar.
        const numero = campoNumero.value.trim();
        const cep = campoCep.value.trim();
        let endereco = campoEndereco.value.trim();
        if (numero) endereco = endereco.replace(/^([^,-]+)/, "$1, " + numero);
        if (cep) endereco += " - CEP " + cep;
        campoEndereco.value = endereco;
    });
});
