# Teste do AWS WAF — Passo a Passo

Este documento explica, passo a passo, **como testar o AWS WAF** deste laboratório e confirmar que o padrão de XSS é bloqueado no endpoint protegido.

> Substitua `SEU-DOMINIO.com` pelos seus subdomínios reais.

---

## O que vamos testar

A ideia é comparar os dois endpoints enviando **duas requisições** para cada um:

| Requisição | O que envia | SEM WAF | COM WAF |
|---|---|---|---|
| Normal | `?search=teste` | 200 | 200 |
| XSS controlado | `?search=<script>alert(1)</script>` | 200 | **403 BLOCKED** |

O payload de XSS é apenas uma **string** com padrão característico de ataque. **Nenhum script é executado** — o objetivo é verificar se o WAF identifica e bloqueia a requisição.

---

## Antes de testar (pré-requisitos)

Confirme que a implantação foi concluída ([IMPLANTACAO.md](IMPLANTACAO.md)):

- [ ] As duas distribuições CloudFront estão com status **Implantado (Deployed)**.
- [ ] Os registros `s3-sem-waf` e `s3-com-waf` existem no Route 53 e o DNS já resolve.
- [ ] O certificado ACM está **Emitido** e o HTTPS funciona.
- [ ] A Web ACL `waf-lab-xss` está **associada** à distribuição COM WAF.

> **Regra de uso:** execute os testes **somente** contra os dois endpoints deste laboratório. Sem flood, sem stress test, sem DDoS. São 4 requisições no total.

---

## Método 1 — Teste pelo navegador (mais visual)

### Passo 1 — Requisição normal SEM WAF

1. Abra no navegador:
   ```
   https://s3-sem-waf.SEU-DOMINIO.com/
   ```
2. **Esperado:** o site do laboratório carrega normalmente (HTTP 200).

### Passo 2 — Requisição XSS SEM WAF

1. Abra:
   ```
   https://s3-sem-waf.SEU-DOMINIO.com/?search=<script>alert(1)</script>
   ```
2. **Esperado:** a página ainda carrega (não há WAF para bloquear). Tende a **200**.
   - Observação: nenhum alerta será exibido — o conteúdo é estático e o payload é só um texto na URL.

### Passo 3 — Requisição normal COM WAF

1. Abra:
   ```
   https://s3-com-waf.SEU-DOMINIO.com/
   ```
2. **Esperado:** o site carrega normalmente (HTTP 200). O WAF permite requisições sem padrão de ataque.

### Passo 4 — Requisição XSS COM WAF

1. Abra:
   ```
   https://s3-com-waf.SEU-DOMINIO.com/?search=<script>alert(1)</script>
   ```
2. **Esperado:** uma página de erro **HTTP 403 (Forbidden)** do CloudFront/WAF. A requisição foi **bloqueada** pela regra `Block-XSS-Lab` antes de chegar ao S3.

> Dica: se o navegador estiver com cache, force o recarregamento (Ctrl+F5) ou abra em uma aba anônima.

---

## Método 2 — Teste com os scripts (mais rápido e padronizado)

Os scripts fazem as 4 requisições automaticamente e mostram os códigos HTTP lado a lado. Eles tratam o **403 como resultado esperado** (não como erro).

### Opção A — Python

Requer Python 3 (usa apenas a biblioteca padrão).

```bash
python tests/test-xss.py --sem-waf https://s3-sem-waf.SEU-DOMINIO.com --com-waf https://s3-com-waf.SEU-DOMINIO.com
```

### Opção B — PowerShell

No Windows:

```powershell
.\tests\test-xss.ps1 -UrlSemWaf "https://s3-sem-waf.SEU-DOMINIO.com" -UrlComWaf "https://s3-com-waf.SEU-DOMINIO.com"
```

### Saída esperada (nos dois casos)

```
========================================
AWS WAF LAB 01 - XSS
========================================

SEM WAF
  Normal.................... 200
  XSS....................... 200

COM WAF
  Normal.................... 200
  XSS....................... 403 BLOCKED

========================================
```

Se a linha `XSS` do bloco **COM WAF** mostrar **403 BLOCKED**, o WAF está funcionando corretamente.

---

## Método 3 — Página do laboratório (gera as URLs para você)

1. Abra `https://s3-sem-waf.SEU-DOMINIO.com/` (ou o outro endpoint).
2. Vá até a seção **Teste Controlado**.
3. Preencha os campos **URL SEM WAF** e **URL COM WAF** com os seus endpoints.
4. Clique em **Gerar URLs de teste**.
5. A página monta as quatro URLs (normal e XSS, já com **URL encoding** aplicado no payload).
6. Copie cada URL e abra no navegador para validar os códigos, como no Método 1.

> A página **não dispara** requisições — ela apenas monta as URLs corretas para você testar manualmente.

---

## Passo final — Confirmar o bloqueio no CloudWatch / WAF

Depois de rodar o teste de XSS contra o endpoint COM WAF, confirme o bloqueio nas métricas.

### Ver as métricas de bloqueio

1. No Console, abra **WAF & Shield > Web ACLs**.
2. Confirme o escopo **Global (CloudFront)** (região us-east-1) e abra a Web ACL **`waf-lab-xss`**.
3. Na aba **Visão geral (Overview)**, veja os gráficos:
   - **Solicitações permitidas (AllowedRequests)** — as requisições normais.
   - **Solicitações bloqueadas (BlockedRequests)** — deve aumentar após o teste de XSS.

### Ver as solicitações amostradas (Sampled Requests)

1. Ainda na Web ACL `waf-lab-xss`, abra a aba **Solicitações de amostra (Sampled requests)**.
2. Selecione a janela de tempo do seu teste.
3. Localize a requisição de XSS. Ela deve aparecer com:
   - **Ação: BLOCK**
   - **Regra correspondente: `Block-XSS-Lab`**
   - A URI / query string contendo o padrão `<script>...`.

Isso confirma que a regra **`Block-XSS-Lab`** foi a responsável pelo bloqueio.

> As métricas e amostras podem levar alguns minutos para aparecer.

---

## Interpretando os resultados

| Resultado observado | Significado |
|---|---|
| COM WAF + XSS → **403** | ✅ WAF funcionando: padrão de XSS bloqueado. |
| COM WAF + XSS → 200 | ⚠️ WAF não bloqueou. Veja "Se o teste falhar" abaixo. |
| SEM WAF + XSS → 200 | ✅ Esperado (não há WAF nesse endpoint). |
| SEM WAF + XSS → 403 | ⚠️ Essa distribuição não deveria ter Web ACL associada. |
| Qualquer endpoint + normal → 403 | ⚠️ Provável problema de OAC / política do bucket, não de WAF. |

---

## Se o teste falhar (COM WAF não bloqueia o XSS)

Verifique, nesta ordem:

1. A Web ACL `waf-lab-xss` está **associada** à distribuição COM WAF?
   - CloudFront > distribuição COM WAF > aba **Segurança** > **AWS WAF**.
2. A regra `Block-XSS-Lab` está com **Ação = Block** (e não Count)?
3. A regra inspeciona a **query string / todos os parâmetros de consulta**?
4. A regra tem a **transformação de texto URL decode** (ideal também HTML entity decode)?
5. Você aguardou a propagação após alterar o WAF? Mudanças levam alguns instantes.
6. O navegador pode estar com cache — teste com Ctrl+F5, aba anônima ou pelos scripts.

Se o problema for **403 em requisições normais** (não relacionadas a XSS), o mais provável é a política do bucket / OAC, não o WAF — confira a Etapa 5 do [IMPLANTACAO.md](IMPLANTACAO.md).
