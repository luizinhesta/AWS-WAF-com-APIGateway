# Teste do AWS WAF — Passo a Passo

Este documento explica, passo a passo, **como testar o AWS WAF** deste laboratório e comprovar que o padrão de SQL Injection é bloqueado no stage protegido — inclusive mostrando que a **Lambda não é executada** quando o WAF bloqueia.

> Substitua `SEU-DOMINIO.com` pelos seus subdomínios reais.

---

## O que vamos testar

Enviamos **três requisições** para cada endpoint e comparamos:

| Requisição | O que envia | SEM WAF | COM WAF |
|---|---|---|---|
| Health | `GET /health` | 200 | 200 |
| Normal | `GET /produto?id=123` | 200 | 200 |
| SQL Injection | `GET /produto?id=1' OR '1'='1` | 200 (Lambda executa) | **403 BLOCKED** (Lambda não executa) |

O payload `1' OR '1'='1` é enviado apenas como **texto** no parâmetro `id`. **Não existe banco de dados nem execução de SQL** — a Lambda apenas ecoa o parâmetro. O objetivo é verificar se o WAF inspeciona e bloqueia.

---

## Antes de testar (pré-requisitos)

Confirme que a implantação ([IMPLANTACAO.md](IMPLANTACAO.md)) foi concluída:

- [ ] A Lambda `lambda-waf-lab03` está implantada (Deploy feito).
- [ ] A REST API tem os stages `sem-waf` e `com-waf` implantados.
- [ ] Os Custom Domains `api-sem-waf` e `api-com-waf` estão mapeados e resolvem no DNS.
- [ ] A Web ACL `waf-lab-sqli` está **associada** ao stage `com-waf`.

> **Regra de uso:** execute os testes **somente** contra os seus próprios endpoints. Sem flood, sem stress test, sem DDoS. São 6 requisições no total.

---

## Método 1 — Teste pelo navegador

### SEM WAF

1. `https://api-sem-waf.SEU-DOMINIO.com/health` → JSON de health (200).
2. `https://api-sem-waf.SEU-DOMINIO.com/produto?id=123` → `{"status":"success","id":"123",...}` (200).
3. `https://api-sem-waf.SEU-DOMINIO.com/produto?id=1' OR '1'='1` → a Lambda **executa** e ecoa o parâmetro (200).

### COM WAF

1. `https://api-com-waf.SEU-DOMINIO.com/health` → 200.
2. `https://api-com-waf.SEU-DOMINIO.com/produto?id=123` → 200.
3. `https://api-com-waf.SEU-DOMINIO.com/produto?id=1' OR '1'='1` → **HTTP 403** (bloqueado pela regra `Block-SQLi-Lab`).

> No navegador, o payload com espaços e aspas é codificado automaticamente. Nos scripts, o **URL encoding** é aplicado explicitamente.

---

## Método 2 — Teste com os scripts

### Python

```bash
python tests/test-sqli.py --sem-waf https://api-sem-waf.SEU-DOMINIO.com --com-waf https://api-com-waf.SEU-DOMINIO.com
```

### PowerShell

```powershell
.\tests\test-sqli.ps1 -ApiSemWaf "https://api-sem-waf.SEU-DOMINIO.com" -ApiComWaf "https://api-com-waf.SEU-DOMINIO.com"
```

### Saída esperada

```
=========================================
AWS WAF LAB 03 - SQL INJECTION
=========================================

SEM WAF
  Health..................... 200
  Normal..................... 200
  SQL Injection.............. 200

COM WAF
  Health..................... 200
  Normal..................... 200
  SQL Injection.............. 403 BLOCKED

=========================================
```

---

## Passo principal — Comprovar que a Lambda NÃO executou

Esta é a **evidência central** do laboratório: SEM WAF a chamada de SQLi chega à Lambda; COM WAF ela é bloqueada e a Lambda **não** é invocada.

### A) CloudWatch Logs da Lambda

1. Console: **CloudWatch > Grupos de logs (Log groups) > `/aws/lambda/lambda-waf-lab03`**.
2. Abra o **fluxo de log** mais recente (ou use **Live Tail** para acompanhar em tempo real).
3. **Execute primeiro o teste SEM WAF** com o SQLi:
   ```
   https://api-sem-waf.SEU-DOMINIO.com/produto?id=1' OR '1'='1
   ```
   - Deve aparecer uma linha de log com `"event": "request"`, `"path": ".../produto"`, `"requestId": ...` e o `id_param` recebido. Isso comprova que a **Lambda executou**.
4. **Agora execute o teste COM WAF** com o SQLi:
   ```
   https://api-com-waf.SEU-DOMINIO.com/produto?id=1' OR '1'='1
   ```
   - O cliente recebe **403**.
   - **Nenhuma** nova linha correspondente deve aparecer no log da Lambda — o WAF bloqueou antes da integração. A Lambda **não executou**.

> Dica: faça os dois testes com alguns segundos de intervalo para distinguir claramente as entradas (ou a ausência delas) no log.

### B) Métrica Invocations da Lambda

1. **CloudWatch > Métricas > Lambda > By Function Name > `lambda-waf-lab03`**.
2. Observe a métrica **`Invocations`**:
   - Incrementa após o teste **SEM WAF**.
   - **Não** incrementa com o teste **COM WAF** bloqueado.

---

## Passo final — CloudWatch (WAF e API Gateway)

### Métricas do WAF

1. **WAF & Shield > Web ACLs > `waf-lab-sqli`** (na região da API).
2. Aba **Visão geral**: **AllowedRequests** (normais) e **BlockedRequests** (aumenta após o SQLi).
3. Aba **Solicitações de amostra (Sampled requests)**: localize a requisição com **Ação: BLOCK** e **Regra: `Block-SQLi-Lab`**.

### Métricas do API Gateway

Em **CloudWatch > Métricas > ApiGateway**, filtre pela API `api-waf-lab03` e observe:

| Métrica | O que indica |
|---|---|
| `Count` | Total de requisições na API. |
| `4XXError` | Erros 4xx (o 403 do WAF aparece aqui no stage `com-waf`). |
| `5XXError` | Erros 5xx (deve permanecer em 0). |
| `Latency` | Tempo de resposta. |

---

## Resultado comparativo

| Teste | SEM WAF | COM WAF |
|---|---|---|
| Normal | Lambda executa | Lambda executa |
| SQLi | Lambda executa | WAF bloqueia |
| HTTP | 200 | 403 |

---

## Interpretando os resultados

| Resultado observado | Significado |
|---|---|
| COM WAF + SQLi → **403** e sem log na Lambda | ✅ WAF funcionando: bloqueou antes da Lambda. |
| COM WAF + SQLi → 200 e com log na Lambda | ⚠️ WAF não bloqueou. Veja "Se o teste falhar". |
| SEM WAF + SQLi → 200 e com log na Lambda | ✅ Esperado (não há WAF nesse stage). |
| COM WAF + Normal/Health → 403 | ⚠️ Regra bloqueando demais — revise a instrução SQLi. |

---

## Se o teste falhar (COM WAF não bloqueia)

Verifique, nesta ordem:

1. A Web ACL `waf-lab-sqli` está **associada ao stage `com-waf`**?
2. A regra `Block-SQLi-Lab` está com **Ação = Block**?
3. A regra inspeciona a **query string / todos os parâmetros de consulta**?
4. A **transformação de texto URL decode** está aplicada?
5. Aguardou a propagação após alterar o WAF?
6. Está testando pelo domínio **`api-com-waf`** (stage `com-waf`) e não pelo `api-sem-waf`?

Se o problema for **403 em rotas normais** (health/produto), a regra pode estar mal configurada — revise para que só o padrão de SQLi seja bloqueado.
