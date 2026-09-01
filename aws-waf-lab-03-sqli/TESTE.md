# Teste do AWS WAF — Passo a Passo

Este documento explica, passo a passo, **como testar o AWS WAF** deste laboratório e comprovar que o padrão de SQL Injection é bloqueado no stage protegido — inclusive mostrando que a **Lambda não é executada** quando o WAF bloqueia.

> Substitua `SEU-DOMINIO.com` pelos seus subdomínios reais.

---

## O que vamos testar

Enviamos **três requisições** para cada endpoint e comparamos:

O laboratório tem **duas proteções** no stage `com-waf`:

1. **Regra SQLi (`Block-SQLi-Lab`)** — bloqueia o padrão de SQL Injection na query string.
2. **Regra de Geo-bloqueio (`Block-Fora-do-Brasil`)** — bloqueia **qualquer** requisição cujo IP de origem esteja **fora do Brasil**.

### Teste A — SQL Injection (acessando a partir do Brasil)

| Requisição | O que envia | SEM WAF | COM WAF (do Brasil) |
|---|---|---|---|
| Health | `GET /health` | 200 | 200 |
| Normal | `GET /produto?id=123` | 200 | 200 |
| SQL Injection | `GET /produto?id=1' OR '1'='1` | 200 (Lambda executa) | **403 BLOCKED** (Lambda não executa) |

O payload `1' OR '1'='1` é enviado apenas como **texto** no parâmetro `id`. **Não existe banco de dados nem execução de SQL** — a Lambda apenas ecoa o parâmetro. O objetivo é verificar se o WAF inspeciona e bloqueia.

### Teste B — Geo-bloqueio (acessando de fora do Brasil)

| Requisição | Origem | COM WAF |
|---|---|---|
| Health | IP fora do Brasil | **403 BLOCKED** |
| Normal (`?id=123`) | IP fora do Brasil | **403 BLOCKED** |
| Qualquer rota | IP fora do Brasil | **403 BLOCKED** |

Quando a origem está fora do Brasil, a regra `Block-Fora-do-Brasil` bloqueia **antes** de qualquer inspeção de SQLi. Por isso **todas** as rotas do `com-waf` retornam 403 — inclusive `/health` e requisições totalmente normais. O stage `sem-waf` continua acessível de qualquer país.

---

## Antes de testar (pré-requisitos)

Confirme que a implantação ([IMPLANTACAO.md](IMPLANTACAO.md)) foi concluída:

- [ ] A Lambda `lambda-waf-lab03` está implantada (Deploy feito).
- [ ] A REST API tem os stages `sem-waf` e `com-waf` implantados.
- [ ] Os Custom Domains `api-sem-waf` e `api-com-waf` estão mapeados e resolvem no DNS.
- [ ] A Web ACL `waf-lab-sqli` está **associada** ao stage `com-waf`.
- [ ] A Web ACL tem as **duas regras**: `Block-SQLi-Lab` e `Block-Fora-do-Brasil` (ambas com ação **Block**).
- [ ] Para o Teste B, você tem como sair por um **IP fora do Brasil** (VPN ou instância em outra região/país).

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

O script `tests/test-sqli.py` usa **apenas a biblioteca padrão** do Python 3 — não precisa instalar nenhum pacote adicional (sem `pip install`).

#### 1. Instalar o Python

- **Windows:**
  - Opção A (recomendada): abra o **PowerShell** e rode `winget install Python.Python.3.12`.
  - Opção B: baixe o instalador em [python.org/downloads](https://www.python.org/downloads/) e, na primeira tela do instalador, marque **Add python.exe to PATH** antes de clicar em *Install Now*.
- **macOS:** já costuma vir com Python 3; se precisar, instale com `brew install python` ([Homebrew](https://brew.sh/)).
- **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install -y python3`.

Confirme a instalação (feche e reabra o terminal após instalar):

```powershell
python --version
```

Deve exibir algo como `Python 3.12.x`. No macOS/Linux, se `python` não funcionar, use `python3 --version`.

#### 2. Ir até a pasta do projeto

Execute os comandos **a partir da raiz do projeto** `aws-waf-lab-03-sqli` (a pasta que contém a pasta `tests`). No Windows/PowerShell:

```powershell
cd c:\github\WAF\aws-waf-lab-03-sqli
```

> Ajuste o caminho se você clonou o repositório em outro lugar. Para conferir que está na pasta certa, rode `dir` (Windows) ou `ls` (macOS/Linux) e verifique se aparece a pasta `tests`.

#### 3. Executar o script

```bash
python tests/test-sqli.py --sem-waf https://api-sem-waf.SEU-DOMINIO.com --com-waf https://api-com-waf.SEU-DOMINIO.com
```

> No macOS/Linux, se `python` não existir, troque por `python3` no início do comando.

### PowerShell

O PowerShell já vem instalado no Windows — não precisa instalar nada. Execute também **a partir da raiz do projeto**:

```powershell
cd c:\github\WAF\aws-waf-lab-03-sqli
.\tests\test-sqli.ps1 -ApiSemWaf "https://api-sem-waf.SEU-DOMINIO.com" -ApiComWaf "https://api-com-waf.SEU-DOMINIO.com"
```

> Se aparecer um erro de política de execução ao rodar o `.ps1`, libere apenas a sessão atual com:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

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

## Teste do Geo-bloqueio — bloquear acesso de fora do Brasil

Esta é a comprovação da regra `Block-Fora-do-Brasil`: quem acessa de **fora do Brasil** recebe **403** em qualquer rota; quem acessa **do Brasil** continua passando (e só é barrado pela regra SQLi quando envia o payload).

### Como simular um IP de fora do Brasil

Escolha **uma** das opções abaixo. Nenhuma delas ataca terceiros — você só está mudando o **seu** IP de origem para demonstrar a geolocalização.

- **Opção 1 — VPN:** conecte-se a um servidor VPN em outro país (ex.: Estados Unidos, Portugal). Antes de testar, confirme o país do seu IP em um site do tipo "meu IP" (por exemplo, `https://ipinfo.io`). Certifique-se de que o país exibido **não** é o Brasil.
- **Opção 2 — Instância em outra região/país:** suba uma instância EC2 pequena em uma região fora do Brasil (ex.: `us-east-1`) e rode os testes de dentro dela (via SSM Session Manager). O IP público da instância será geolocalizado fora do Brasil.
- **Opção 3 — Celular em roaming / outro país:** se estiver fisicamente em outro país ou com um IP estrangeiro, também serve.

> A regra usa o **IP de origem** (Source IP). Se você usa proxy corporativo, VPN sempre ligada, ou está atrás de um NAT que sai por outro país, o resultado pode variar — confirme sempre o país real do seu IP antes de concluir.

### Passo 1 — De dentro do Brasil (linha de base)

1. Confirme (em um site de "meu IP") que seu IP está no **Brasil**.
2. Acesse:
   ```
   https://api-com-waf.SEU-DOMINIO.com/health
   ```
   **Esperado:** **200** (o geo-bloqueio não barra o Brasil).
3. Acesse a rota normal:
   ```
   https://api-com-waf.SEU-DOMINIO.com/produto?id=123
   ```
   **Esperado:** **200**.

### Passo 2 — De fora do Brasil (bloqueio esperado)

1. Ative a **VPN** (ou use a instância em outra região) e confirme que seu IP agora está **fora do Brasil**.
2. Acesse a rota de health (totalmente inofensiva):
   ```
   https://api-com-waf.SEU-DOMINIO.com/health
   ```
   **Esperado:** **HTTP 403** — bloqueado pela regra `Block-Fora-do-Brasil`, mesmo sem nenhum payload malicioso.
3. Acesse a rota normal:
   ```
   https://api-com-waf.SEU-DOMINIO.com/produto?id=123
   ```
   **Esperado:** **HTTP 403** (o geo-bloqueio barra qualquer rota).
4. Para contraste, acesse o stage **sem WAF** de fora do Brasil:
   ```
   https://api-sem-waf.SEU-DOMINIO.com/health
   ```
   **Esperado:** **200** — o `sem-waf` não tem WAF, então aceita qualquer país.

### Passo 3 — Comprovar no CloudWatch / Sampled requests

1. **WAF & Shield > Web ACLs > `waf-lab-sqli` > aba Solicitações de amostra (Sampled requests)**.
2. Localize a requisição vinda de fora do Brasil, com **Ação: BLOCK** e **Regra: `Block-Fora-do-Brasil`**.
3. Nas colunas da amostra, o **país (Country)** da requisição bloqueada deve ser diferente de **BR**.

### Resultado do Geo-bloqueio

| Origem | Rota | Resultado |
|---|---|---|
| Brasil | `/health`, `/produto?id=123` | 200 (passa) |
| Brasil | `/produto?id=1' OR '1'='1` | 403 (regra SQLi) |
| Fora do Brasil | qualquer rota | 403 (regra `Block-Fora-do-Brasil`) |

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
| COM WAF + Normal/Health → 403 **de fora do Brasil** | ✅ Esperado: a regra `Block-Fora-do-Brasil` barra qualquer rota vinda de fora do país. |
| COM WAF + Normal/Health → 403 **de dentro do Brasil** | ⚠️ Regra bloqueando demais. Se for a geo, o NOT (Negate) pode estar invertido; se for a SQLi, revise a instrução. |
| COM WAF de fora do Brasil → 200 | ⚠️ Geo-bloqueio não atuou. Confirme o país real do IP e a regra `Block-Fora-do-Brasil`. |

---

## Se o teste falhar (COM WAF não bloqueia)

Verifique, nesta ordem:

1. A Web ACL `waf-lab-sqli` está **associada ao stage `com-waf`**?
2. A regra `Block-SQLi-Lab` está com **Ação = Block**?
3. A regra inspeciona a **query string / todos os parâmetros de consulta**?
4. A **transformação de texto URL decode** está aplicada?
5. Aguardou a propagação após alterar o WAF?
6. Está testando pelo domínio **`api-com-waf`** (stage `com-waf`) e não pelo `api-sem-waf`?

Se o problema for **403 em rotas normais** (health/produto) **acessando de dentro do Brasil**, a regra pode estar mal configurada — revise para que só o padrão de SQLi seja bloqueado, e confirme que a regra `Block-Fora-do-Brasil` está com o **Negate statement** ativo (senão ela bloqueia o próprio Brasil).

### Se o Geo-bloqueio não funcionar (de fora do Brasil ainda passa)

Verifique, nesta ordem:

1. Seu IP de teste **realmente** sai por outro país? Confirme em um site de "meu IP" — a VPN pode estar com servidor no Brasil.
2. A regra `Block-Fora-do-Brasil` tem **Ação = Block**?
3. Na instrução geográfica, o país selecionado é **Brazil - BR** e o botão **Negate statement results** está **ativo**?
4. A regra está inspecionando o **Source IP address** (IP de origem)?
5. Aguardou a propagação após criar/alterar a regra?
6. Está testando pelo domínio **`api-com-waf`** (stage `com-waf`) e não pelo `api-sem-waf`?
