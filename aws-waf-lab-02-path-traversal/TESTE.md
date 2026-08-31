# Teste do AWS WAF — Passo a Passo

Este documento explica, passo a passo, **como testar o AWS WAF** deste laboratório e comprovar que o padrão de Path Traversal é bloqueado no endpoint protegido — inclusive pela **ausência da requisição no `access.log`** do Nginx.

> Substitua `SEU-DOMINIO.com` pelos seus subdomínios reais.

---

## O que vamos testar

Enviamos **duas requisições** para cada endpoint e comparamos:

| Requisição | O que envia | SEM WAF | COM WAF |
|---|---|---|---|
| Normal | `?file=relatorio.txt` | chega ao Nginx (200/404) | chega ao Nginx (200/404) |
| Path Traversal | `?file=../../etc/passwd` | **chega ao Nginx** | **403 BLOCKED** |

O padrão `../../etc/passwd` é enviado apenas como **texto** no parâmetro `file`. **Nenhum arquivo do sistema é lido** — a aplicação ignora o parâmetro. O objetivo é só verificar se o WAF inspeciona e bloqueia.

---

## Antes de testar (pré-requisitos)

Confirme que a implantação ([IMPLANTACAO.md](IMPLANTACAO.md)) foi concluída:

- [ ] A EC2 está **Healthy** nos dois Target Groups.
- [ ] Os dois ALBs respondem por HTTPS.
- [ ] Os registros `alb-sem-waf` e `alb-com-waf` resolvem no DNS.
- [ ] A Web ACL `waf-lab-path-traversal` está **associada** ao `alb-com-waf-lab02`.

> **Regra de uso:** execute os testes **somente** contra a sua própria infraestrutura. Sem flood, sem stress test, sem DDoS. São 4 requisições no total.

---

## Método 1 — Teste pelo navegador (mais visual)

### Passo 1 — Normal SEM WAF

```
https://alb-sem-waf.SEU-DOMINIO.com/
```
**Esperado:** o site do laboratório carrega (HTTP 200).

### Passo 2 — Path Traversal SEM WAF

```
https://alb-sem-waf.SEU-DOMINIO.com/?file=../../etc/passwd
```
**Esperado:** a página ainda responde (200 ou 404) — a requisição **chega ao Nginx**. Nenhum arquivo é retornado; o parâmetro é ignorado.

### Passo 3 — Normal COM WAF

```
https://alb-com-waf.SEU-DOMINIO.com/
```
**Esperado:** o site carrega normalmente (HTTP 200).

### Passo 4 — Path Traversal COM WAF

```
https://alb-com-waf.SEU-DOMINIO.com/?file=../../etc/passwd
```
**Esperado:** página de erro **HTTP 403** — bloqueado pela regra `Block-Path-Traversal-Lab` antes de chegar ao ALB/EC2.

> Variação com URL encoding para testar a transformação de texto do WAF: `?file=%2e%2e%2fetc%2fpasswd`.

---

## Método 2 — Teste com os scripts (mais rápido)

Os scripts fazem as 4 requisições e mostram os resultados lado a lado. Eles tratam `403` como **BLOCKED** e outros códigos (200/404) como **"chegou ao servidor"**.

### Python

```bash
python tests/test-path-traversal.py --sem-waf https://alb-sem-waf.SEU-DOMINIO.com --com-waf https://alb-com-waf.SEU-DOMINIO.com
```

### PowerShell

```powershell
.\tests\test-path-traversal.ps1 -UrlSemWaf "https://alb-sem-waf.SEU-DOMINIO.com" -UrlComWaf "https://alb-com-waf.SEU-DOMINIO.com"
```

### Saída esperada

```
===========================================
AWS WAF LAB 02 - PATH TRAVERSAL
===========================================

SEM WAF
  Normal...................... 200
  Path Traversal.............. chegou ao servidor (404)

COM WAF
  Normal...................... 200
  Path Traversal.............. 403 BLOCKED

===========================================
```

Se a linha `Path Traversal` do bloco **COM WAF** mostrar **403 BLOCKED**, o WAF está funcionando.

---

## Passo principal — Comprovação no access.log do Nginx

Esta é a **evidência central** do laboratório: mostrar que a requisição de Path Traversal **chega** ao servidor SEM WAF e **não chega** COM WAF.

### 1. Abrir o log da EC2 via SSM

1. Console: **Systems Manager > Session Manager > Iniciar sessão** na `ec2-waf-lab02`.
2. Acompanhe o log em tempo real:
   ```bash
   sudo tail -f /var/log/nginx/access.log
   ```

### 2. Executar o teste SEM WAF (deve aparecer no log)

- Em outra aba/navegador, acesse:
  ```
  https://alb-sem-waf.SEU-DOMINIO.com/?file=../../etc/passwd
  ```
- **No `access.log`** deve surgir uma linha contendo a requisição, algo como:
  ```
  10.0.x.x - - [.. data ..] "GET /?file=../../etc/passwd HTTP/1.1" 200 ...
  ```
- Isso comprova que a requisição **chegou ao Nginx** (não havia WAF para bloquear).

### 3. Executar o teste COM WAF (NÃO deve aparecer no log)

- Acesse:
  ```
  https://alb-com-waf.SEU-DOMINIO.com/?file=../../etc/passwd
  ```
- No **cliente**, você recebe **HTTP 403**.
- **No `access.log`** da EC2 **não** deve aparecer nenhuma linha correspondente a essa requisição — o WAF bloqueou no ALB, antes de encaminhar ao Target Group.

> Dica: para separar bem as evidências, faça primeiro só o teste SEM WAF, observe o log, e só depois faça o COM WAF. A ausência da linha no log após o 403 é o resultado que queremos demonstrar.

---

## Passo final — CloudWatch (WAF e ALB)

### Métricas do WAF

1. **WAF & Shield > Web ACLs > `waf-lab-path-traversal`** (na região do ALB).
2. Aba **Visão geral (Overview)**:
   - **Solicitações permitidas (AllowedRequests)** — requisições normais.
   - **Solicitações bloqueadas (BlockedRequests)** — deve aumentar após o teste de Path Traversal.
3. Aba **Solicitações de amostra (Sampled requests)**: localize a requisição bloqueada, com **Ação: BLOCK** e **Regra: `Block-Path-Traversal-Lab`**.

### Métricas do ALB

Em **CloudWatch > Métricas > AWS/ApplicationELB**, filtre pelos seus ALBs e observe:

| Métrica | O que indica |
|---|---|
| `RequestCount` | Total de requisições processadas pelo ALB. |
| `HTTPCode_ELB_4XX_Count` | Respostas 4xx geradas pelo ELB (inclui os 403 do WAF no ALB COM WAF). |
| `HealthyHostCount` | Número de alvos saudáveis no Target Group (deve ser ≥ 1). |
| `UnHealthyHostCount` | Alvos não saudáveis (deve ser 0). |

---

## Interpretando os resultados

| Resultado observado | Significado |
|---|---|
| COM WAF + Path Traversal → **403** e ausente no log | ✅ WAF funcionando: bloqueou antes da aplicação. |
| COM WAF + Path Traversal → 200/404 e presente no log | ⚠️ WAF não bloqueou. Veja "Se o teste falhar". |
| SEM WAF + Path Traversal → presente no log | ✅ Esperado (não há WAF nesse caminho). |
| Alvo Unhealthy / 502 / 504 | ⚠️ Problema de EC2/Nginx/health check, não de WAF. |

---

## Se o teste falhar (COM WAF não bloqueia)

Verifique, nesta ordem:

1. A Web ACL `waf-lab-path-traversal` está **associada** ao `alb-com-waf-lab02`?
   - WAF > Web ACLs > Recursos AWS associados.
2. A regra `Block-Path-Traversal-Lab` está com **Ação = Block**?
3. A regra inspeciona a **query string** (e/ou o URI Path) procurando `../`?
4. A **transformação de texto URL decode** está aplicada (para pegar `%2e%2e%2f`)?
5. Aguardou a propagação após alterar o WAF?
6. Cache do navegador — teste com Ctrl+F5, aba anônima ou pelos scripts.

Se o problema for **alvo Unhealthy / 502 / 504** (não relacionado ao WAF), confira Nginx, o endpoint `/health` e o Security Group da EC2 na Etapa correspondente do [IMPLANTACAO.md](IMPLANTACAO.md).
