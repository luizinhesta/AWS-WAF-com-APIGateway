# Teste do AWS WAF — Passo a Passo

Este documento explica, passo a passo, **como testar o AWS WAF** deste laboratório e comprovar que o padrão de Path Traversal é bloqueado no endpoint protegido — inclusive pela **ausência da requisição no `access.log`** do Nginx.

> Substitua `SEU-DOMINIO.com` pelos seus subdomínios reais.

---

## O que vamos testar

O laboratório tem **duas proteções** no `alb-com-waf-lab02`:

1. **Regra de Path Traversal (`Block-Path-Traversal-Lab`)** — bloqueia o padrão `../` na query string (ação **Block**).
2. **Regra de CAPTCHA por país (`Captcha-Fora-do-Brasil`)** — exige um **CAPTCHA** para requisições cujo IP de origem esteja **fora do Brasil** (ação **CAPTCHA**). Do Brasil, o acesso é direto.

### Teste A — Path Traversal (acessando a partir do Brasil)

| Requisição | O que envia | SEM WAF | COM WAF (do Brasil) |
|---|---|---|---|
| Normal | `?file=relatorio.txt` | chega ao Nginx (200/404) | chega ao Nginx (200/404) |
| Path Traversal | `?file=../../etc/passwd` | **chega ao Nginx** | **403 BLOCKED** |

O padrão `../../etc/passwd` é enviado apenas como **texto** no parâmetro `file`. **Nenhum arquivo do sistema é lido** — a aplicação ignora o parâmetro. O objetivo é só verificar se o WAF inspeciona e bloqueia.

### Teste B — CAPTCHA (acessando de fora do Brasil, pelo navegador)

| Requisição | Origem | COM WAF |
|---|---|---|
| Acesso normal ao site (`/`) | Brasil | site carrega direto (200) |
| Acesso normal ao site (`/`) | fora do Brasil | **página de CAPTCHA** → site só carrega após resolver |
| Path Traversal | fora do Brasil | **403 BLOCKED** (Block vence o CAPTCHA) |

O CAPTCHA do WAF é uma **página interativa** que só é resolvida em um **navegador** (que executa JavaScript). Scripts como curl/`Invoke-WebRequest` recebem **HTTP 405** com o corpo do desafio, sem resolvê-lo — por isso o Teste B é feito **pelo navegador**.

---

## Antes de testar (pré-requisitos)

Confirme que a implantação ([IMPLANTACAO.md](IMPLANTACAO.md)) foi concluída:

- [ ] A EC2 está **Healthy** nos dois Target Groups.
- [ ] Os dois ALBs respondem por HTTPS.
- [ ] Os registros `alb-sem-waf` e `alb-com-waf` resolvem no DNS.
- [ ] A Web ACL `waf-lab-path-traversal` está **associada** ao `alb-com-waf-lab02`.
- [ ] A Web ACL tem as **duas regras**: `Block-Path-Traversal-Lab` (ação **Block**) e `Captcha-Fora-do-Brasil` (ação **CAPTCHA**).
- [ ] Para o Teste B, você tem como sair por um **IP fora do Brasil** (VPN ou instância em outro país) e um **navegador** para resolver o CAPTCHA.

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

O script `tests/test-path-traversal.py` usa **apenas a biblioteca padrão** do Python 3 — não precisa instalar nenhum pacote adicional (sem `pip install`).

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

Execute os comandos **a partir da raiz do projeto** `aws-waf-lab-02-path-traversal` (a pasta que contém a pasta `tests`). No Windows/PowerShell:

```powershell
cd c:\github\WAF\aws-waf-lab-02-path-traversal
```

> Ajuste o caminho se você clonou o repositório em outro lugar. Para conferir que está na pasta certa, rode `dir` (Windows) ou `ls` (macOS/Linux) e verifique se aparece a pasta `tests`.

#### 3. Executar o script

```bash
python tests/test-path-traversal.py --sem-waf https://alb-sem-waf.SEU-DOMINIO.com --com-waf https://alb-com-waf.SEU-DOMINIO.com
```

> No macOS/Linux, se `python` não existir, troque por `python3` no início do comando.

### PowerShell

O PowerShell já vem instalado no Windows — não precisa instalar nada. Execute também **a partir da raiz do projeto**:

```powershell
cd c:\github\WAF\aws-waf-lab-02-path-traversal
.\tests\test-path-traversal.ps1 -UrlSemWaf "https://alb-sem-waf.SEU-DOMINIO.com" -UrlComWaf "https://alb-com-waf.SEU-DOMINIO.com"
```

> Se aparecer um erro de política de execução ao rodar o `.ps1`, libere apenas a sessão atual com:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

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

## Teste do CAPTCHA — acesso ao site apenas do Brasil (ou após resolver o desafio)

Esta é a comprovação da regra `Captcha-Fora-do-Brasil`: quem acessa **do Brasil** entra direto; quem acessa **de fora do Brasil** recebe uma **página de CAPTCHA** e só chega ao site depois de resolvê-la.

> **Use o navegador.** O CAPTCHA precisa de JavaScript para ser resolvido. Os scripts (`test-path-traversal.py/ps1`, curl) **não** conseguem resolver o desafio — recebem **HTTP 405** com o corpo do CAPTCHA. Isso é esperado e, por si só, já demonstra que o WAF interceptou o acesso de fora do Brasil.

### Como simular um IP de fora do Brasil

Escolha **uma** das opções (você só muda o **seu** IP de origem, não ataca ninguém):

- **VPN:** conecte-se a um servidor em outro país (ex.: Estados Unidos, Portugal). Confirme o país do seu IP em um site do tipo "meu IP" (ex.: `https://ipinfo.io`) — precisa **não** ser o Brasil.
- **Instância em outra região/país:** suba uma EC2 pequena fora do Brasil e abra o site de dentro dela por um navegador (ou navegador remoto). O IP público será geolocalizado fora do Brasil.

### Passo 1 — De dentro do Brasil (acesso direto)

1. Confirme (em site de "meu IP") que seu IP está no **Brasil**.
2. No navegador, acesse:
   ```
   https://alb-com-waf.SEU-DOMINIO.com/
   ```
   **Esperado:** o site carrega **direto** (HTTP 200), **sem** página de CAPTCHA — o Brasil não é desafiado.

### Passo 2 — De fora do Brasil (CAPTCHA obrigatório)

1. Ative a **VPN** (ou use a instância em outra região) e confirme que seu IP agora está **fora do Brasil**.
2. No navegador, acesse:
   ```
   https://alb-com-waf.SEU-DOMINIO.com/
   ```
   **Esperado:** em vez do site, aparece a **página de CAPTCHA do AWS WAF** ("Verifique que você é humano" / desafio visual).
3. **Resolva o CAPTCHA.**
   **Esperado:** após resolver, o navegador é liberado e o **site carrega normalmente**. Durante o tempo de **imunidade** (ex.: 300s) você não precisa refazer o desafio.
4. **Recarregue** a página dentro do tempo de imunidade.
   **Esperado:** o site carrega direto (o token de CAPTCHA ainda é válido).

### Passo 3 — De fora do Brasil, com Path Traversal (Block vence o CAPTCHA)

1. Ainda de fora do Brasil (VPN ligada), acesse:
   ```
   https://alb-com-waf.SEU-DOMINIO.com/?file=../../etc/passwd
   ```
   **Esperado:** **HTTP 403** (bloqueado pela regra `Block-Path-Traversal-Lab`), **não** a página de CAPTCHA — o path traversal é bloqueado antes, pois a regra de Block tem prioridade mais alta.

### Passo 4 — Comprovar no CloudWatch / Sampled requests

1. **WAF & Shield > Web ACLs > `waf-lab-path-traversal` > aba Solicitações de amostra (Sampled requests)**.
2. Localize a requisição vinda de fora do Brasil com **Ação: CAPTCHA** e **Regra: `Captcha-Fora-do-Brasil`**. O **país (Country)** deve ser diferente de **BR**.
3. Observe também que o acesso vindo do Brasil **não** aparece com ação CAPTCHA (ele passa direto).

> No `access.log` do Nginx: o acesso de fora do Brasil só aparece **depois** que o CAPTCHA é resolvido (quando a requisição é finalmente encaminhada ao ALB/EC2). Antes de resolver, o WAF responde o desafio e a requisição **não** chega ao Nginx.

### Resultado do CAPTCHA

| Origem | Requisição | Resultado |
|---|---|---|
| Brasil | `/` (site) | Carrega direto (200) |
| Fora do Brasil | `/` (site, navegador) | Página de CAPTCHA → site após resolver |
| Fora do Brasil | `/` (via script) | HTTP 405 com corpo do CAPTCHA (não resolve) |
| Fora do Brasil | `?file=../../etc/passwd` | 403 (Block do path traversal) |

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
| COM WAF + site de fora do Brasil → **página de CAPTCHA** | ✅ Regra `Captcha-Fora-do-Brasil` funcionando. |
| COM WAF + site do Brasil → **CAPTCHA** aparece | ⚠️ Provável Negate invertido — a regra está desafiando o Brasil. |
| COM WAF + site de fora do Brasil (via script) → **405** | ✅ Esperado: scripts não resolvem CAPTCHA; use o navegador. |
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

### Se o CAPTCHA não funcionar como esperado

Verifique, nesta ordem:

1. Seu IP de teste **realmente** sai por outro país? Confirme em um site de "meu IP" — a VPN pode estar com servidor no Brasil.
2. Você está testando pelo **navegador**? Scripts não resolvem CAPTCHA (recebem 405).
3. A regra `Captcha-Fora-do-Brasil` está com **Ação = CAPTCHA**?
4. Na instrução geográfica, o país é **Brazil - BR** e o **Negate statement results** está **ativo**? (Sem o NOT, a regra desafia justamente o Brasil.)
5. A regra inspeciona o **Source IP address**?
6. Aguardou a propagação após criar/alterar a regra? Teste em aba anônima para evitar token de CAPTCHA/cache antigos.
7. Se de fora do Brasil o site abre **direto** (sem CAPTCHA): confirme que a regra existe, está habilitada e associada ao `alb-com-waf-lab02`.
