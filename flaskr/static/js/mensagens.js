document.addEventListener("DOMContentLoaded", function() {
    
    // 1. Configura os botões de Adicionar ao Carrinho (Aluguel e Comum)
    const botoesCarrinho = [
        { seletor: ".btn-carrinho-aluguel", texto: "🛒 Adicionado ao carrinho (aluguel) com sucesso!" },
        { seletor: ".btn-carrinho-comum", texto: "🛒 Adicionado ao carrinho com sucesso!" }
    ];

    botoesCarrinho.forEach(item => {
        const botao = document.querySelector(item.seletor);
        if (botao) {
            botao.addEventListener("click", () => mostrarToast(item.texto, "#28a745"));
        }
    });

    // 2. Configura os botões de Confirmação (Alugar Agora e Comprar Agora)
    const botoesConfirmacao = [
        { seletor: ".btn-alugar-agora", mensagem: "Deseja confirmar a locação deste item?" },
        { seletor: ".btn-comprar-agora", mensagem: "Deseja confirmar a compra deste item?" }
    ];

    botoesConfirmacao.forEach(item => {
        const botao = document.querySelector(item.seletor);
        if (botao) {
            botao.addEventListener("click", function(event) {
                if (!confirm(item.mensagem)) {
                    event.preventDefault(); // Cancela o envio se clicar em Cancelar
                }
            });
        }
    });

    // Função auxiliar para criar o aviso flutuante (Toast)
    function mostrarToast(texto, corFundo) {
        const toast = document.createElement("div");
        toast.innerText = texto;
        
        Object.assign(toast.style, {
            position: "fixed",
            top: "20px",
            right: "20px",
            backgroundColor: corFundo,
            color: "#fff",
            padding: "12px 20px",
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
            zIndex: "9999",
            fontWeight: "600",
            fontFamily: "sans-serif",
            transition: "opacity 0.5s ease"
        });

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }
});