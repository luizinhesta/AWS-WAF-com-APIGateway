# Teste do AWS WAF — Passo a Passo

Este documento explica, passo a passo, **como testar o AWS WAF** deste laboratório e confirmar que o padrão de XSS é bloqueado no endpoint protegido.

> Substitua `SEU-DOMINIO.com` pelos seus subdomínios reais.

---

## O que vamos testar

O endpoint COM WAF tem **duas proteções**:

1. **Regra de XSS (`Block-XSS-Lab`)** — bloqueia o padrão de XSS na query string (403 padrão).
2. **Regra de Geo-bloqueio (`Block-Fora-do-Brasil`)** — bloqueia **qualquer** requisição cujo IP de origem esteja **fora do Brasil**, respondendo com uma **página HTML de acesso negado** (403 personalizado).

### Teste A — XSS (acessando a partir do Brasil)

| Requisição | O que envia | SEM WAF | COM WAF (do Brasil) |
|---|---|---|---|
| Normal | `?search=teste` | 200 | 200 |
| XSS controlado | `?search=<script>alert(1)</script>` | 200 | **403 BLOCKED** |

O payload de XSS é apenas uma **string** com padrão característico de ataque. **Nenhum script é executado** — o objetivo é verificar se o WAF identifica e bloqueia a requisição.

### Teste B — Geo-bloqueio (acessando de fora do Brasil)

| Requisição | Origem | COM WAF |
|---|---|---|
| Qualquer rota (ex.: `/`) | Brasil | 200 (passa) |
| Qualquer rota (ex.: `/`) | fora do Brasil | **403 com a página "Acesso negado"** |

De fora do Brasil, a regra `Block-Fora-do-Brasil` bloqueia **antes** da inspeção de XSS e retorna a página HTML personalizada (`site/acesso-negado.html`). O endpoint SEM WAF continua acessível de qualquer país.

---

## Antes de testar (pré-requisitos)

Confirme que a implantação foi concluída ([IMPLANTACAO.md](IMPLANTACAO.md)):

- [ ] As duas distribuições CloudFront estão com status **Implantado (Deployed)**.
- [ ] Os registros `site-sem-waf` e `site-com-waf` existem no Route 53 e o DNS já resolve.
- [ ] O certificado ACM está **Emitido** e o HTTPS funciona.
- [ ] A Web ACL `waf-lab-xss` está **associada** à distribuição COM WAF.
- [ ] A Web ACL tem as **duas regras**: `Block-XSS-Lab` e `Block-Fora-do-Brasil` (ação **Block**).
- [ ] O corpo de resposta personalizado `acesso-negado-br` está cadastrado e vinculado à regra de geo.
- [ ] Para o Teste B, você tem como sair por um **IP fora do Brasil** (VPN ou instância em outro país).

> **Regra de uso:** execute os testes **somente** contra os dois endpoints deste laboratório. Sem flood, sem stress test, sem DDoS. São 4 requisições no total.

---

## Método 1 — Teste pelo navegador (mais visual)

### Passo 1 — Requisição normal SEM WAF

1. Abra no navegador:
   ```
   https://site-sem-waf.SEU-DOMINIO.com/
   ```
2. **Esperado:** o site do laboratório carrega normalmente (HTTP 200).

### Passo 2 — Requisição XSS SEM WAF

1. Abra:
   ```
   https://site-sem-waf.SEU-DOMINIO.com/?search=<script>alert(1)</script>
   ```
2. **Esperado:** a página ainda carrega (não há WAF para bloquear). Tende a **200**.
   - Observação: nenhum alerta será exibido — o conteúdo é estático e o payload é só um texto na URL.

### Passo 3 — Requisição normal COM WAF

1. Abra:
   ```
   https://site-com-waf.SEU-DOMINIO.com/
   ```
2. **Esperado:** o site carrega normalmente (HTTP 200). O WAF permite requisições sem padrão de ataque.

### Passo 4 — Requisição XSS COM WAF

1. Abra:
   ```
   https://site-com-waf.SEU-DOMINIO.com/?search=<script>alert(1)</script>
   ```
2. **Esperado:** uma página de erro **HTTP 403 (Forbidden)** do CloudFront/WAF. A requisição foi **bloqueada** pela regra `Block-XSS-Lab` antes de chegar ao S3.

> Dica: se o navegador estiver com cache, force o recarregamento (Ctrl+F5) ou abra em uma aba anônima.

---

## Método 2 — Teste com os scripts (mais rápido e padronizado)

Os scripts fazem as 4 requisições automaticamente e mostram os códigos HTTP lado a lado. Eles tratam o **403 como resultado esperado** (não como erro).

### Opção A — Python

O script `tests/test-xss.py` usa **apenas a biblioteca padrão** do Python 3 — não precisa instalar nenhum pacote adicional (sem `pip install`).

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

Execute os comandos **a partir da raiz do projeto** `aws-waf-lab-01-xss` (a pasta que contém a pasta `tests`). No Windows/PowerShell:

```powershell
cd c:\github\WAF\aws-waf-lab-01-xss
```

> Ajuste o caminho se você clonou o repositório em outro lugar. Para conferir que está na pasta certa, rode `dir` (Windows) ou `ls` (macOS/Linux) e verifique se aparece a pasta `tests`.

#### 3. Executar o script

```bash
python tests/test-xss.py --sem-waf https://site-sem-waf.SEU-DOMINIO.com --com-waf https://site-com-waf.SEU-DOMINIO.com
```

> No macOS/Linux, se `python` não existir, troque por `python3` no início do comando.

### Opção B — PowerShell

O PowerShell já vem instalado no Windows — não precisa instalar nada. Execute também **a partir da raiz do projeto**:

```powershell
cd c:\github\WAF\aws-waf-lab-01-xss
.\tests\test-xss.ps1 -UrlSemWaf "https://site-sem-waf.SEU-DOMINIO.com" -UrlComWaf "https://site-com-waf.SEU-DOMINIO.com"
```

> Se aparecer um erro de política de execução ao rodar o `.ps1`, libere apenas a sessão atual com:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

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

1. Abra `https://site-sem-waf.SEU-DOMINIO.com/` (ou o outro endpoint).
2. Vá até a seção **Teste Controlado**.
3. Preencha os campos **URL SEM WAF** e **URL COM WAF** com os seus endpoints.
4. Clique em **Gerar URLs de teste**.
5. A página monta as quatro URLs (normal e XSS, já com **URL encoding** aplicado no payload).
6. Copie cada URL e abra no navegador para validar os códigos, como no Método 1.

> A página **não dispara** requisições — ela apenas monta as URLs corretas para você testar manualmente.

---

## Teste do Geo-bloqueio — página de acesso negado para fora do Brasil

Esta é a comprovação da regra `Block-Fora-do-Brasil`: quem acessa de **fora do Brasil** recebe **HTTP 403** com a **página HTML de acesso negado**; quem acessa **do Brasil** continua entrando normalmente.

### Como simular um IP de fora do Brasil

Escolha **uma** das opções (você só muda o **seu** IP de origem, não ataca ninguém):

- **VPN:** conecte-se a um servidor em outro país (ex.: Estados Unidos, Portugal). Confirme o país do seu IP em um site do tipo "meu IP" (ex.: `https://ipinfo.io`) — precisa **não** ser o Brasil.
- **Instância em outra região/país:** suba uma EC2 pequena fora do Brasil e teste de dentro dela. O IP público será geolocalizado fora do Brasil.

### Passo 1 — De dentro do Brasil (acesso normal)

1. Confirme (em site de "meu IP") que seu IP está no **Brasil**.
2. No navegador, acesse:
   ```
   https://site-com-waf.SEU-DOMINIO.com/
   ```
   **Esperado:** o site carrega normalmente (HTTP 200) — o Brasil não é bloqueado.

### Passo 2 — De fora do Brasil (página de acesso negado)

1. Ative a **VPN** (ou use a instância em outra região) e confirme que seu IP agora está **fora do Brasil**.
2. No navegador, acesse:
   ```
   https://site-com-waf.SEU-DOMINIO.com/
   ```
   **Esperado:** em vez do site, aparece a **página "Você não tem acesso a este site"** (a `acesso-negado.html`), com status **HTTP 403**.
3. Para conferir o código HTTP, abra as **Ferramentas do desenvolvedor (F12) > aba Network**, recarregue e veja o status **403** na requisição do documento — com o corpo HTML personalizado.
4. Para contraste, acesse o endpoint **sem WAF** de fora do Brasil:
   ```
   https://site-sem-waf.SEU-DOMINIO.com/
   ```
   **Esperado:** **200** — o SEM WAF não tem WAF, então aceita qualquer país.

> Os scripts de teste (`test-xss.py` / `.ps1`) também recebem **403** de fora do Brasil, mas eles só mostram o **código HTTP** — a página de acesso negado é vista mesmo é **pelo navegador**.

### Passo 3 — Comprovar no CloudWatch / Sampled requests

1. **WAF & Shield > Web ACLs > `waf-lab-xss`** (escopo CloudFront/global) **> aba Solicitações de amostra (Sampled requests)**.
2. Localize a requisição vinda de fora do Brasil com **Ação: BLOCK** e **Regra: `Block-Fora-do-Brasil`**. O **país (Country)** deve ser diferente de **BR**.

### Resultado do Geo-bloqueio

| Origem | Requisição | Resultado |
|---|---|---|
| Brasil | `/` (ou qualquer rota) | 200 (passa) |
| Brasil | `?search=<script>alert(1)</script>` | 403 (regra XSS) |
| Fora do Brasil | qualquer rota | 403 + página "Acesso negado" (regra geo) |

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
| COM WAF + qualquer rota **de fora do Brasil** → 403 com a página de acesso negado | ✅ Geo-bloqueio funcionando. |
| COM WAF + qualquer rota **do Brasil** → 403/página de acesso negado | ⚠️ Regra de geo invertida — o **Negate** pode estar desligado, bloqueando o próprio Brasil. |
| COM WAF de fora do Brasil → 200 | ⚠️ Geo-bloqueio não atuou. Confirme o país real do IP e a regra `Block-Fora-do-Brasil`. |
| Qualquer endpoint + normal (do Brasil) → 403 | ⚠️ Provável problema de OAC / política do bucket, não de WAF. |

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

Se o problema for **403 em requisições normais** (não relacionadas a XSS) **acessando do Brasil**, verifique primeiro se não é a regra de geo com o **Negate** invertido; se não for, o mais provável é a política do bucket / OAC, não o WAF — confira a Etapa 5 do [IMPLANTACAO.md](IMPLANTACAO.md).

### Se o Geo-bloqueio não funcionar (de fora do Brasil ainda passa) ou a página não aparecer

Verifique, nesta ordem:

1. Seu IP de teste **realmente** sai por outro país? Confirme em um site de "meu IP" — a VPN pode estar com servidor no Brasil.
2. A regra `Block-Fora-do-Brasil` tem **Ação = Block**?
3. Na instrução geográfica, o país é **Brazil - BR** e o **NOT / Negate statement results** está **ativo**? (Sem o NOT, ela bloqueia o próprio Brasil.)
4. A regra inspeciona o **Source IP address**?
5. Se o bloqueio ocorre mas aparece o **403 padrão** (sem a página personalizada): confirme que a **Resposta personalizada** está habilitada na regra, com **código 403** e o corpo **`acesso-negado-br`** selecionado.
6. Aguardou a propagação do CloudFront/WAF após alterar a regra? Teste em aba anônima para evitar cache.
