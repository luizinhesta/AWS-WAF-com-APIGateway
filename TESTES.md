# Guia de Testes de Validação — AWS WAF Security Lab 03 (SQL Injection)

Este documento reúne os **testes de validação** do laboratório **AWS WAF Security Lab — Projeto 03: Proteção contra SQL Injection com API Gateway REST + AWS Lambda**. Ele comprova, de forma prática e reproduzível, que a **única** diferença observável entre os dois ambientes é a presença do AWS WAF no stage `com-waf`.

> **Pré-requisito:** execute estes testes **após** concluir a implantação descrita em [`IMPLANTACAO.md`](./IMPLANTACAO.md) (Fases 1 a 16) e **antes** da exclusão descrita em [`EXCLUSAO.md`](./EXCLUSAO.md).

## Convenções deste guia

- Substitua **`DOMINIO`** pelo seu domínio real, gerenciado em uma zona hospedada (Hosted zone) existente no Route 53 (por exemplo, `exemplo.com.br`).
- Os pontos marcados com **📸 Evidência / Print recomendado** indicam onde capturar telas para comprovação.
- **SQL Injection de teste:** `GET /produto?id=1' OR '1'='1`. Payload usado **apenas** para acionar a inspeção do WAF — a rota `/produto` apenas ecoa o parâmetro, **não** há vulnerabilidade real, **não** há banco de dados e **não** há execução de SQL.

---

## Convenções e recursos usados nos testes

Substitua `DOMINIO` pelo domínio de sua propriedade gerenciado na Zona Hospedada do Route 53.

| Item | Valor |
|---|---|
| Stage sem WAF | `sem-waf` |
| Stage com WAF | `com-waf` |
| Custom Domain sem WAF | `api-sem-waf.DOMINIO` (endpoint regional, mapeado ao stage `sem-waf`) |
| Custom Domain com WAF | `api-com-waf.DOMINIO` (endpoint regional, mapeado ao stage `com-waf`) |
| URL base sem WAF | `https://api-sem-waf.DOMINIO` |
| URL base com WAF | `https://api-com-waf.DOMINIO` |
| Web ACL | `waf-lab-sqli` (Regional, ação padrão ALLOW, associada somente ao `com-waf`) |
| Regra de geo (prioridade 1) | `Block-Fora-do-Brasil` (ação BLOCK) |
| Regra de SQLi (prioridade 2) | `Block-SQLi-Lab` (ação BLOCK) |
| Grupo de logs | CloudWatch Logs `/aws/lambda/{nome-da-funcao}` |
| Métrica de invocação | Namespace `AWS/Lambda`, métrica `Invocations` |

**Scripts de teste da API.** Os cenários podem ser executados com `curl` (comandos individuais) ou pelos scripts do laboratório, que executam o conjunto de requisições por ambiente:

```bash
# Python (multiplataforma)
python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf
python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf
```

```powershell
# PowerShell
./tests/test-sqli.ps1 -BaseUrl https://api-sem-waf.DOMINIO -Environment sem-waf
./tests/test-sqli.ps1 -BaseUrl https://api-com-waf.DOMINIO -Environment com-waf
```

Os scripts apresentam, para cada requisição, o endpoint testado, o código HTTP recebido, o esperado e o veredito (aprovado/reprovado), e retornam código de saída 0 somente se todos os testes forem aprovados.

> **Como ler cada cenário:** cada cenário indica **URL**, **comando**, **resultado esperado**, **código HTTP**, **onde verificar** e **evidência a coletar**.

---
## Cenário 1 — `sem-waf`: Health check (`/health`)

![Descrição da imagem](<imagens/imagem%20(3).png>)

Confirma que a API e a Lambda respondem antes dos demais testes, no ambiente sem WAF.

- **URL:** `https://api-sem-waf.DOMINIO/health`
- **Comando (curl):**
  ```bash
  curl -i https://api-sem-waf.DOMINIO/health
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf` (teste "Health check").
- **Resultado esperado:** corpo JSON `{"status":"healthy","project":"AWS WAF Security Lab 03"}`.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script (linha de status e corpo).
- **Evidência a coletar:** print/log do comando mostrando `HTTP/1.1 200` e o corpo JSON.

---

## Cenário 2 — `sem-waf`: Rota de produto (`/produto`)

![Descrição da imagem](<imagens/imagem%20(4).png>)

Confirma que a rota de eco responde 200 no ambiente sem WAF com um parâmetro simples.

- **URL:** `https://api-sem-waf.DOMINIO/produto?id=123`
- **Comando (curl):**
  ```bash
  curl -i "https://api-sem-waf.DOMINIO/produto?id=123"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf` (teste "Produto (parametro simples)").
- **Resultado esperado:** corpo JSON com o valor ecoado idêntico ao recebido, ex.: `{"id":"123"}`.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo `{"id":"123"}`.

---

## Cenário 3 — `sem-waf`: SQL Injection de teste processada (200)

![Descrição da imagem](<imagens/imagem%20(5).png>)

Comprova que, **sem WAF**, a requisição com padrão de SQL Injection **alcança a Lambda** e é processada normalmente (a rota apenas ecoa o parâmetro).

- **URL:** `https://api-sem-waf.DOMINIO/produto?id=1' OR '1'='1`
- **Comando (curl):** (a query é codificada em URL)
  ```bash
  curl -i "https://api-sem-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf` (teste "SQL Injection de teste").
- **Resultado esperado:** a requisição é processada e o valor recebido é ecoado no campo `id` sem alteração; resposta em até 3000 ms.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script. A comprovação por CloudWatch é detalhada no Cenário 7.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo com o `id` ecoado. Anote o horário do envio para correlacionar com o CloudWatch (Cenário 7).

---

## Cenário 4 — `com-waf`: Health check (`/health`)

![Descrição da imagem](<imagens/imagem%20(6).png>)

Confirma que o ambiente protegido responde normalmente a tráfego legítimo (do Brasil), sem bloqueio, na rota de health.

- **URL:** `https://api-com-waf.DOMINIO/health`
- **Comando (curl):**
  ```bash
  curl -i https://api-com-waf.DOMINIO/health
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf` (teste "Health check").
- **Resultado esperado:** corpo JSON `{"status":"healthy","project":"AWS WAF Security Lab 03"}`. Como a requisição não casa com nenhuma regra e a origem é o Brasil, a ação padrão ALLOW permite que ela alcance a API.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo JSON.

> **Pré-condição:** executar a partir de uma origem **no Brasil**. A partir de fora do Brasil, a regra `Block-Fora-do-Brasil` retorna `403` (ver a seção de Geo-bloqueio ao final deste documento).

---

## Cenário 5 — `com-waf`: Rota de produto (`/produto`)

![Descrição da imagem](<imagens/imagem%20(7).png>)

Confirma que uma requisição legítima à rota de eco, sem padrão de SQLi, é permitida (ALLOW) no ambiente protegido.

- **URL:** `https://api-com-waf.DOMINIO/produto?id=123`
- **Comando (curl):**
  ```bash
  curl -i "https://api-com-waf.DOMINIO/produto?id=123"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf` (teste "Produto (parametro simples)").
- **Resultado esperado:** corpo JSON com o valor ecoado, ex.: `{"id":"123"}`. A Web ACL permite a requisição (não há padrão de SQLi e a origem é o Brasil).
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo `{"id":"123"}`.

> **Pré-condição:** executar a partir de uma origem **no Brasil** (ver observação do Cenário 4).

---

## Cenário 6 — `com-waf`: SQL Injection de teste bloqueada (403)

![Descrição da imagem](<imagens/imagem%20(8).png>)
![Descrição da imagem](<imagens/imagem%20(9).png>)

Comprova que, **com WAF**, a requisição de SQL Injection de teste é **bloqueada pela regra `Block-SQLi-Lab`** antes de alcançar a API. Este é o cenário central do laboratório.

- **URL:** `https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1`
- **Comando (curl):** (a query é codificada em URL)
  ```bash
  curl -i "https://api-com-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf` (teste "SQL Injection de teste").
- **Resultado esperado:** a Web ACL `waf-lab-sqli` bloqueia a requisição pela regra `Block-SQLi-Lab` (a origem no Brasil passa pela regra `Block-Fora-do-Brasil`, mas casa com a regra de SQLi de prioridade 2), respondendo em até 5 segundos e impedindo que a requisição alcance a API/Lambda.
- **Código HTTP:** `403`.
- **Onde verificar:** saída do `curl`/script; corpo típico de bloqueio do WAF (mensagem de "Forbidden"). A ausência de execução da Lambda é comprovada no Cenário 7; a evidência do WAF é coletada no Cenário 8 (e no Cenário 9).
- **Evidência a coletar:** print mostrando `HTTP/1.1 403`. Anote o horário do envio para correlacionar com o CloudWatch (Cenário 7) e com as Sampled requests (Cenário 8).

> **Pré-condição:** executar a partir de uma origem **no Brasil**. A partir de fora do Brasil o `403` também ocorreria, porém pela regra `Block-Fora-do-Brasil` (prioridade 1), e não pela regra de SQLi — ver a seção de Geo-bloqueio ao final.

---

## Cenário 7 — Verificação por CloudWatch: chegada (sem WAF) x bloqueio (com WAF) na Lambda

Comprova, por duas fontes independentes do CloudWatch da **mesma** Lambda, que a SQL Injection de teste **chega e executa** a Lambda no `sem-waf` e **não chega** no `com-waf`. Como os dois stages compartilham a mesma Lambda e o mesmo grupo de logs, a ausência de nova entrada e o incremento zero da métrica no `com-waf` provam que o WAF interrompeu a requisição **antes** da integração Lambda Proxy.

Realize este cenário logo após enviar a SQL Injection de teste nos Cenários 3 (`sem-waf`) e 6 (`com-waf`), correlacionando pelos horários anotados.

### 7.a — `sem-waf`: nova entrada de log e Invocations = 1

- **Envio (referência):** SQL Injection de teste pelo stage `sem-waf` (Cenário 3).
- **Onde verificar (logs):** CloudWatch Logs → grupo de logs `/aws/lambda/{nome-da-funcao}` → fluxo de log mais recente.
- **Resultado esperado (logs):** **nova entrada de execução** contendo o `requestId` (identificador de requisição), o método `GET` e o caminho `/produto`, dentro de uma janela de observação de **no mínimo 60 segundos** após o envio.
- **Onde verificar (métrica):** CloudWatch → Métricas → namespace `AWS/Lambda` → métrica `Invocations` da função, filtrada pelo horário do envio.
- **Resultado esperado (métrica):** `Invocations = 1` para essa requisição.
- **Evidência a coletar:** print da entrada de log destacando o `requestId`; print do gráfico/valor de `Invocations = 1`.

### 7.b — `com-waf`: ausência de nova entrada e Invocations = 0

- **Envio (referência):** SQL Injection de teste pelo stage `com-waf` (Cenário 6), que retornou `403`.
- **Onde verificar (logs):** mesmo grupo de logs `/aws/lambda/{nome-da-funcao}`.
- **Resultado esperado (logs):** **nenhuma nova entrada de execução** para essa requisição durante a janela de observação de **no mínimo 60 segundos** após o envio (a Lambda não executou porque o WAF bloqueou antes da integração).
- **Onde verificar (métrica):** namespace `AWS/Lambda`, métrica `Invocations`, filtrada pelo horário do envio.
- **Resultado esperado (métrica):** `Invocations = 0` (métrica inalterada) para essa requisição.
- **Evidência a coletar:** print do grupo de logs mostrando a ausência de nova entrada na janela de 60s; print de `Invocations = 0` no período.

### Resumo esperado da comprovação

| Cenário | Stage | HTTP | Nova entrada no log? | Invocations |
|---|---|---|---|---|
| SQL Injection de teste | `sem-waf` | 200 | Sim (com `requestId`) | 1 |
| SQL Injection de teste | `com-waf` (do Brasil) | 403 | Não | 0 |

### Critério de FALHA (janela de 60s)

Se a **entrada de execução esperada não for encontrada** no grupo de logs `/aws/lambda/{nome-da-funcao}` dentro da janela de observação de **60 segundos**, registre o resultado da verificação como **FALHA**, indicando:

- o **stage** avaliado (`sem-waf` ou `com-waf`);
- o **`requestId`** esperado (ausente).

Aplica-se, por exemplo, ao caso 7.a: se a nova entrada com o `requestId` do envio pelo `sem-waf` não aparecer em 60s, o cenário é uma **FALHA** (a comprovação de chegada à Lambda não foi obtida).

![Descrição da imagem](<imagens/imagem%20(15).png>)

---

## Cenário 8 — Evidências de bloqueio nas Sampled requests do WAF

Coleta a evidência do bloqueio na própria ferramenta, consultando as Solicitações de amostra (Sampled requests) da Web ACL.

- **Onde verificar:** Console do AWS WAF → Web ACLs → `waf-lab-sqli` → aba de **Solicitações de amostra (Sampled requests)** (é possível filtrar por regra e período; correlacione pelo horário do envio no Cenário 6).
- **Resultado esperado:** a amostra da SQL Injection de teste enviada pelo `com-waf` deve mostrar:
  - a **regra que correspondeu**: `Block-SQLi-Lab`;
  - a **ação**: `BLOCK`;
  - a **origem** (Source IP) da requisição;
  - o **código HTTP** associado ao bloqueio: `403`.
- **Evidência a coletar:** print da linha de amostra destacando `Block-SQLi-Lab`, ação `BLOCK`, a origem e o `403`.

> Observação: as Sampled requests dependem de a Web ACL estar coletando amostras no período consultado. Envie a SQL Injection de teste (Cenário 6) e consulte a amostra em seguida, filtrando pelo intervalo do envio.

---

## Cenário 9 — Consolidação e comparação entre ambientes

Fecha a comparação didática consolidando os resultados dos cenários anteriores, deixando explícita a única diferença observável entre os ambientes: a presença do WAF no `com-waf`.

- **Comando (execução consolidada dos scripts):**
  ```bash
  python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf
  python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf
  ```
  ou, em PowerShell:
  ```powershell
  ./tests/test-sqli.ps1 -BaseUrl https://api-sem-waf.DOMINIO -Environment sem-waf
  ./tests/test-sqli.ps1 -BaseUrl https://api-com-waf.DOMINIO -Environment com-waf
  ```
- **Resultado esperado (tabela consolidada):**

  | # | Requisição | Stage | HTTP esperado |
  |---|---|---|---|
  | 1 | `GET /health` | `sem-waf` | 200 |
  | 2 | `GET /produto?id=123` | `sem-waf` | 200 |
  | 3 | SQL Injection de teste | `sem-waf` | 200 |
  | 4 | `GET /health` | `com-waf` | 200 |
  | 5 | `GET /produto?id=123` | `com-waf` | 200 |
  | 6 | SQL Injection de teste | `com-waf` | 403 (`Block-SQLi-Lab`) |

- **Código HTTP:** conforme a tabela acima (a única inversão de comportamento entre os stages é a SQL Injection de teste: `200` no `sem-waf` e `403` no `com-waf`).
- **Onde verificar:** saída dos scripts (resumo com veredito e código de saída) somada às evidências dos Cenários 7 (CloudWatch) e 8 (Sampled requests).
- **Evidência a coletar:** print do resumo dos scripts (todos aprovados por ambiente) e a tabela consolidada acima preenchida com os resultados reais observados. Reúna, no mesmo conjunto de evidências, os prints do CloudWatch (Cenário 7) e das Sampled requests (Cenário 8) para comprovar que o `403` do `com-waf` foi gerado pelo WAF antes da Lambda.

---

## Seção de Geo-bloqueio — Regra `Block-Fora-do-Brasil`

Esta seção é dedicada ao teste da **restrição geográfica** do ambiente protegido (stage `com-waf`). A regra `Block-Fora-do-Brasil` (prioridade 1 na Web ACL `waf-lab-sqli`) usa correspondência geográfica com o país **BR** (ISO 3166-1 alpha-2) e **lógica de negação (NOT)**: ela casa (e aplica `BLOCK`) sempre que a origem for **diferente do Brasil**. Como é a **primeira** regra avaliada, requisições de fora do Brasil são bloqueadas **antes** da inspeção de SQL Injection (regra `Block-SQLi-Lab`, prioridade 2).

> **Escopo:** o Geo-bloqueio só existe no stage `com-waf` (única associação da Web ACL). O stage `sem-waf` não possui WAF e, portanto, não aplica restrição geográfica.

![Descrição da imagem](<imagens/imagem%20(16).png>)

### Como a AWS determina a origem geográfica

- A origem geográfica é determinada pela **AWS** a partir do **endereço de origem (Source IP address)** da requisição, mapeado para o país correspondente. Não há como (nem se deve) **forjar** a origem: o teste consiste em executar a requisição a partir de uma rede/host realmente localizado no país desejado.
- **Para testar a partir do Brasil:** basta executar de uma conexão/host localizada no Brasil (o caso comum de quem implanta o laboratório no país).
- **Para testar a partir de fora do Brasil**, use uma origem cujo Source IP esteja fora do país, por exemplo:
  - uma **VPN** com ponto de saída em outro país;
  - uma **instância/host em outra região** da AWS ou de outro provedor (ex.: uma EC2 em `us-east-1`) executando o `curl`/script;
  - qualquer outra rede comprovadamente fora do Brasil.
- **País de origem indeterminado:** quando a AWS **não consegue determinar** o país a partir do Source IP, a requisição é tratada como **fora do Brasil** e recebe `BLOCK` (postura conservadora, *fail-closed*). Ver o cenário G.3.

### Modo geográfico dos scripts de teste

Os scripts do laboratório possuem um **modo geográfico** que executa o conjunto de requisições a partir das duas origens e apresenta os resultados em **blocos separados e identificados** (origem no Brasil e origem fora do Brasil):

```bash
# Python (multiplataforma)
python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf --geo
```

```powershell
# PowerShell (equivalente)
./tests/test-sqli.ps1 -BaseUrl https://api-com-waf.DOMINIO -Environment com-waf -Geo
```

> **Importante:** o modo `--geo`/`-Geo` **não forja** a origem. Ele apenas organiza a saída em dois blocos rotulados; a origem efetiva depende de **onde o script está sendo executado**. Para obter o bloco "fora do Brasil", execute o script de um host/rede fora do país (ex.: instância em outra região ou VPN). O ideal é rodar o script duas vezes — uma de dentro do Brasil e outra de fora — e reunir os dois blocos como evidência.

---

## Cenário G.1 — `com-waf` do Brasil: comportamento normal (origem que passa pela Regra_Geo)

![Descrição da imagem](<imagens/imagem%20(13).png>)

Comprova que, para uma origem **no Brasil**, a regra `Block-Fora-do-Brasil` **não** aplica `BLOCK` e a Web ACL prossegue para as demais regras: o tráfego legítimo responde `200` e apenas a SQL Injection de teste é bloqueada (pela regra de SQLi, e não pela geográfica).

- **Origem:** rede/host **no Brasil**.
- **URLs / requisições:**
  - `https://api-com-waf.DOMINIO/health` → `200`
  - `https://api-com-waf.DOMINIO/produto?id=123` → `200`
  - SQL Injection de teste: `https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1` → `403` (pela regra `Block-SQLi-Lab`, prioridade 2)
- **Comando (curl):**
  ```bash
  curl -i https://api-com-waf.DOMINIO/health
  curl -i "https://api-com-waf.DOMINIO/produto?id=123"
  curl -i "https://api-com-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script — bloco "origem no Brasil"):**
  ```bash
  python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf --geo
  ```
  (executado a partir de uma origem no Brasil; observe o bloco identificado como **origem no Brasil**).
- **Resultado esperado:** `/health` e `/produto?id=123` retornam `200`; a SQL Injection de teste retorna `403` pela regra `Block-SQLi-Lab`. A regra `Block-Fora-do-Brasil` **não** casa (origem = BR) e deixa a avaliação prosseguir.
- **Código HTTP:** `200` (rotas legítimas) e `403` (SQL Injection de teste, pela regra de SQLi).
- **Onde verificar:** saída do `curl`/script (bloco "origem no Brasil"); a distinção da regra que causou o `403` é confirmada nas Sampled requests (ver G.4).
- **Evidência a coletar:** print do bloco "origem no Brasil" mostrando `200` nas rotas legítimas e `403` na SQL Injection de teste; anote o horário para correlacionar com as Sampled requests (regra `Block-SQLi-Lab`).

---

## Cenário G.2 — `com-waf` de fora do Brasil: bloqueio pela regra `Block-Fora-do-Brasil` (403)

![Descrição da imagem](<imagens/imagem%20(18).png>)

Comprova que, para uma origem **fora do Brasil**, **qualquer** requisição ao stage `com-waf` é bloqueada com `403` pela regra `Block-Fora-do-Brasil` (prioridade 1), **antes** da inspeção de SQL Injection. Mesmo requisições legítimas (ex.: `/health`, `/produto?id=123`) são bloqueadas, porque a barreira geográfica é a primeira a ser avaliada.

- **Origem:** rede/host **fora do Brasil** (ex.: VPN com saída em outro país ou instância em outra região). A origem **não** é forjada.
- **URLs / requisições (todas bloqueadas):**
  - `https://api-com-waf.DOMINIO/health` → `403`
  - `https://api-com-waf.DOMINIO/produto?id=123` → `403`
  - SQL Injection de teste: `https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1` → `403` (também pela regra geográfica, pois é avaliada antes da SQLi)
- **Comando (curl, executado de fora do Brasil):**
  ```bash
  curl -i https://api-com-waf.DOMINIO/health
  curl -i "https://api-com-waf.DOMINIO/produto?id=123"
  curl -i "https://api-com-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script — bloco "origem fora do Brasil"):**
  ```bash
  python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf --geo
  ```
  (executado a partir de uma origem fora do Brasil; observe o bloco identificado como **origem fora do Brasil**).
- **Resultado esperado:** **todas** as requisições são bloqueadas com `403` pela regra `Block-Fora-do-Brasil`. A requisição **não** alcança a REST API nem a Lambda (sem execução, sem nova entrada de log, `Invocations` inalterado). A inspeção de SQLi **não** chega a ser aplicada, pois a regra geográfica (prioridade 1) já bloqueou.
- **Código HTTP:** `403` (todas as requisições), gerado pelo próprio WAF.
- **Onde verificar:** saída do `curl`/script (bloco "origem fora do Brasil"); a regra que causou o bloqueio é confirmada nas Sampled requests (ver G.4). A ausência de execução da Lambda pode ser confirmada no CloudWatch, de forma análoga ao Cenário 7 (`Invocations = 0`, sem nova entrada de log).
- **Evidência a coletar:** print do bloco "origem fora do Brasil" mostrando `403` em todas as requisições; anote o horário e a origem (país/IP de saída da VPN ou região da instância) para correlacionar com as Sampled requests (regra `Block-Fora-do-Brasil`).

---

## Cenário G.3 — País de origem indeterminado: tratado como fora do Brasil (403)

Comprova o comportamento *fail-closed* da regra geográfica: quando a AWS **não consegue determinar** o país a partir do Source IP, a requisição é tratada como **fora do Brasil** e recebe `BLOCK` (`403`) pela regra `Block-Fora-do-Brasil` (Requisito 16.7).

- **Origem:** rede/host cujo Source IP **não** é mapeável para um país (origem indeterminada). Este caso pode não ser facilmente reproduzível de forma controlada; quando ocorrer, o comportamento esperado é o descrito abaixo.
- **URLs / requisições:** mesmas do Cenário G.2 — qualquer requisição ao stage `com-waf`.
- **Resultado esperado:** a requisição é tratada como **fora do Brasil** e bloqueada com `403` pela regra `Block-Fora-do-Brasil`, sem alcançar a REST API/Lambda.
- **Código HTTP:** `403` (pela regra `Block-Fora-do-Brasil`).
- **Onde verificar:** saída do `curl`/script e Sampled requests do WAF (regra `Block-Fora-do-Brasil`, ação `BLOCK`).
- **Evidência a coletar:** quando reproduzível, print da amostra mostrando o bloqueio pela regra `Block-Fora-do-Brasil` para a origem sem país determinado; caso não seja possível reproduzir, documente que o comportamento esperado é o mesmo do Cenário G.2 (tratamento como fora do Brasil, `403`).

---

## Cenário G.4 — Evidências de Geo-bloqueio nas Sampled requests do WAF

![Descrição da imagem](<imagens/imagem%20(20).png>)

Coleta a evidência do bloqueio geográfico na própria ferramenta, consultando as Solicitações de amostra (Sampled requests) da Web ACL, de forma análoga ao Cenário 8 (que trata do bloqueio por SQLi).

- **Onde verificar:** Console do AWS WAF → Web ACLs → `waf-lab-sqli` → aba de **Solicitações de amostra (Sampled requests)** (é possível filtrar por regra e período; correlacione pelo horário do envio no Cenário G.2).
- **Resultado esperado:** a amostra da requisição enviada de **fora do Brasil** deve mostrar:
  - a **regra que correspondeu**: `Block-Fora-do-Brasil`;
  - a **ação**: `BLOCK`;
  - a **origem** (Source IP) da requisição, fora do Brasil;
  - o **código HTTP** associado ao bloqueio: `403`.
- **Evidência a coletar:** print da linha de amostra destacando `Block-Fora-do-Brasil`, ação `BLOCK`, a origem (Source IP fora do Brasil) e o `403`.

> Observação: as Sampled requests dependem de a Web ACL estar coletando amostras no período consultado. Envie as requisições de fora do Brasil (Cenário G.2) e consulte a amostra em seguida, filtrando pelo intervalo do envio.

---

## Resumo esperado do Geo-bloqueio

| Origem | Requisição | Stage | HTTP | Regra que bloqueia |
|---|---|---|---|---|
| Brasil | `GET /health` | `com-waf` | 200 | — (ALLOW) |
| Brasil | `GET /produto?id=123` | `com-waf` | 200 | — (ALLOW) |
| Brasil | SQL Injection de teste | `com-waf` | 403 | `Block-SQLi-Lab` (prioridade 2) |
| Fora do Brasil | `GET /health` | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Fora do Brasil | `GET /produto?id=123` | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Fora do Brasil | SQL Injection de teste | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Indeterminada | qualquer requisição | `com-waf` | 403 | `Block-Fora-do-Brasil` (tratada como fora do Brasil) |

A comparação evidencia o efeito da **ordem das regras**: do Brasil, a barreira geográfica é transparente e apenas a SQLi é bloqueada (pela regra de prioridade 2); de fora do Brasil, **tudo** é bloqueado já na regra geográfica (prioridade 1), antes da inspeção de SQLi.

---

## Próximo passo

Após concluir os testes e coletar as evidências, prossiga para a exclusão completa dos recursos em [`EXCLUSAO.md`](./EXCLUSAO.md) para evitar custos remanescentes.
