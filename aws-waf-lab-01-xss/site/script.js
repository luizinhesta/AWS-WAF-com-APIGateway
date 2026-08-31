// AWS WAF Security Lab - Projeto 01 (XSS)
// Gera URLs de teste (normal e XSS controlado) para os dois endpoints do laboratório.
// Nenhuma requisicao e disparada por este script - ele apenas monta as URLs com
// URL encoding aplicado ao payload de XSS.

(function () {
    "use strict";

    // Payload de XSS controlado usado somente contra os endpoints deste laboratorio.
    var XSS_PAYLOAD = "<script>alert(1)</script>";

    function normalizeBase(url) {
        var u = (url || "").trim();
        if (!u) {
            return "";
        }
        // Remove barra final para evitar barras duplicadas.
        return u.replace(/\/+$/, "");
    }

    function buildNormalUrl(base) {
        return base + "/?search=teste";
    }

    function buildXssUrl(base) {
        // encodeURIComponent aplica o URL encoding necessario no payload.
        return base + "/?search=" + encodeURIComponent(XSS_PAYLOAD);
    }

    function setText(id, value) {
        var el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    }

    function onGerar() {
        var semWaf = normalizeBase(document.getElementById("urlSemWaf").value);
        var comWaf = normalizeBase(document.getElementById("urlComWaf").value);

        if (!semWaf || !comWaf) {
            alert("Informe as duas URLs (SEM WAF e COM WAF) do seu laboratorio.");
            return;
        }

        setText("outSemNormal", buildNormalUrl(semWaf));
        setText("outSemXss", buildXssUrl(semWaf));
        setText("outComNormal", buildNormalUrl(comWaf));
        setText("outComXss", buildXssUrl(comWaf));

        document.getElementById("resultado-teste").classList.remove("hidden");
    }

    document.addEventListener("DOMContentLoaded", function () {
        var btn = document.getElementById("btnGerar");
        if (btn) {
            btn.addEventListener("click", onGerar);
        }
    });
})();
