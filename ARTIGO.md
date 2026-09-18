# Protegendo uma API contra SQL Injection com AWS WAF, API Gateway REST e Lambda
![Descrição da imagem](<imagens/imagem%20(1).png>)
> Um laboratório educacional que mostra, na prática, a diferença de comportamento entre uma API **sem** AWS WAF e a **mesma** API **com** AWS WAF, usando uma requisição com padrão de SQL Injection **apenas** para acionar a inspeção do WAF.

---

## Resumo

Este artigo descreve, de ponta a ponta, um laboratório que compara dois ambientes idênticos construídos sobre a **mesma** REST API do API Gateway e a **mesma** função Lambda. A única diferença observável entre eles é a presença do **AWS WAF**: um stage fica sem proteção (grupo de controle) e o outro fica atrás de uma Web ACL com regras de bloqueio geográfico e de SQL Injection.

O objetivo é didático: demonstrar de forma reproduzível que o WAF bloqueia requisições maliciosas **antes** que elas cheguem à aplicação, comprovando isso com evidências independentes do CloudWatch (grupo de logs da Lambda e métrica `Invocations`) e com as Sampled requests da própria Web ACL.

> **Importante:** o laboratório **não** contém vulnerabilidade real, **não** usa banco de dados e **não** executa SQL. A rota `/produto` apenas **ecoa** o parâmetro recebido. O padrão de SQL Injection é usado exclusivamente como gatilho de inspeção do WAF.

---

## Motivação e problema

SQL Injection continua entre as ameaças mais conhecidas a aplicações web. Uma forma de mitigar esse risco na borda, sem depender apenas do código da aplicação, é usar um Web Application Firewall (WAF) que inspeciona e bloqueia requisições suspeitas antes que elas alcancem a lógica de negócio.

A pergunta que o laboratório responde é simples e verificável: **quando adiciono o AWS WAF à frente da minha API, o que muda no comportamento observável?** Para isolar a resposta, o laboratório mantém tudo idêntico entre os dois ambientes (mesma API, mesma Lambda, mesmo código, mesmas rotas) e varia **apenas** a presença do WAF. Assim, qualquer diferença de comportamento é atribuível exclusivamente ao WAF.

---

## Visão geral da solução

O laboratório expõe **dois ambientes** sobre a mesma base:

- **Ambiente SEM WAF** — stage `sem-waf`, sem nenhuma Web ACL associada. Funciona como **grupo de controle**.
- **Ambiente COM WAF** — stage `com-waf`, associado à Web ACL `waf-lab-sqli`. Funciona como **grupo protegido**.

A requisição de teste de SQL Injection é `GET /produto?id=1' OR '1'='1` (usada só para inspeção, sem vulnerabilidade real).

| Requisição | Ambiente | Resultado HTTP | Chega à Lambda? | Invocations (CloudWatch) |
|---|---|---|---|---|
| SQL Injection de teste | `sem-waf` | **200** (id ecoado) | Sim (nova entrada de log com `requestId`) | 1 |
| SQL Injection de teste | `com-waf` (origem no Brasil) | **403** (bloqueado pelo WAF) | Não | 0 |
| Requisição de origem fora do Brasil | `com-waf` | **403** (bloqueado pela regra geográfica) | Não | 0 |

A comprovação de que o WAF bloqueia **antes** da integração Lambda Proxy apoia-se em duas fontes independentes do CloudWatch para a mesma Lambda: o **grupo de logs** `/aws/lambda/{nome-da-funcao}` (nova entrada por execução) e a **métrica `Invocations`** (namespace `AWS/Lambda`). No ambiente `com-waf`, a ausência de nova entrada e o incremento zero da métrica provam que o bloqueio ocorreu no WAF, e não na Lambda.

![Descrição da imagem](<imagens/imagem%20(31).png>)

---

## Serviços AWS utilizados

O laboratório utiliza **somente** os seguintes serviços:

- **Route 53** — hosted zone existente do domínio; registros Alias para os subdomínios.
- **ACM (AWS Certificate Manager)** — certificado TLS regional para os Custom Domains (pode ser curinga `*.DOMINIO`).
- **API Gateway** — 1 REST API (REST, não HTTP), com integração Lambda Proxy.
- **Lambda** — 1 função em Python que trata todas as rotas via roteamento interno.
- **AWS WAF** — 1 Web ACL regional (`waf-lab-sqli`) com 2 regras.
- **CloudWatch** — grupo de logs da Lambda e métrica `Invocations` para comprovar chegada e bloqueio.

> O laboratório **não** usa DynamoDB, RDS, Aurora, EC2, ECS, CloudFront, ALB, NLB, Cognito, SQS, SNS, Bot Control, Fraud Control nem Marketplace Managed Rules. Os endpoints são **regionais** (sem CloudFront na frente da API).

---

## Arquitetura

A arquitetura é fixa e composta por:

- **1 REST API** — `api-waf-lab-sqli` (REST API do API Gateway, **não** HTTP API), integração **Lambda Proxy**, roteamento por `{proxy+}` + `ANY` (mais o recurso raiz `/` com `ANY`).
- **1 Lambda** — `lambda/lambda_function.py`, roteamento interno de todas as rotas.
- **2 stages** — `sem-waf` (sem Web ACL) e `com-waf` (com Web ACL), sobre a mesma API e a mesma Lambda.
- **2 Custom Domains regionais** — `api-sem-waf.DOMINIO` (mapeado ao stage `sem-waf`) e `api-com-waf.DOMINIO` (mapeado ao stage `com-waf`).
- **1 Web ACL regional** — `waf-lab-sqli`, escopo Regional (REGIONAL), ação padrão **ALLOW**, associada **somente** ao stage `com-waf`.
- **2 regras** avaliadas em ordem de prioridade:
  1. **`Block-Fora-do-Brasil`** (prioridade 1) — correspondência geográfica com o país BR e lógica de negação (NOT); ação **BLOCK**.
  2. **`Block-SQLi-Lab`** (prioridade 2) — SQL injection match statement na query string; ação **BLOCK**.

```
                                Internet
                                    |
                     +--------------+--------------+
                     |                             |
           api-sem-waf.DOMINIO            api-com-waf.DOMINIO
                     |                             |
                Route 53                       Route 53
            (Alias regional)               (Alias regional)
                     |                             |
          Custom Domain (regional)      Custom Domain (regional)
                     |                             |
             stage: sem-waf                 stage: com-waf
             (sem Web ACL)                  (Web ACL: waf-lab-sqli)
                     |                    1) Block-Fora-do-Brasil
                     |                    2) Block-SQLi-Lab
                     |                       default: ALLOW
                     +--------------+--------------+
                                    |
                        Integração Lambda Proxy
                                    |
                          Lambda (lambda_function.py)
                                    |
                             CloudWatch Logs
                        /aws/lambda/{funcao} + Invocations
```

### Fluxo SEM WAF (stage `sem-waf`)

1. O cliente resolve `api-sem-waf.DOMINIO` pelo Route 53 (registro Alias para o Custom Domain regional).
2. A requisição chega ao Custom Domain, servido com TLS pelo certificado ACM regional.
3. O API mapping direciona para o stage `sem-waf` da REST API.
4. Como o stage **não** possui Web ACL associada, a requisição segue direto para a integração Lambda Proxy.
5. A Lambda executa, grava log no CloudWatch e incrementa a métrica `Invocations`.
6. A SQL Injection de teste (`GET /produto?id=1' OR '1'='1`) recebe **HTTP 200** com o `id` ecoado.

![Descrição da imagem](<imagens/imagem%20(4).png>)

### Fluxo COM WAF (stage `com-waf`)

1. O cliente resolve `api-com-waf.DOMINIO` pelo Route 53.
2. A requisição chega ao Custom Domain, servido com TLS pelo certificado ACM regional.
3. O API mapping direciona para o stage `com-waf`, que possui a **Web ACL `waf-lab-sqli`** associada.
4. A Web ACL avalia as regras na ordem de prioridade:
   - **1ª — `Block-Fora-do-Brasil`**: se a origem não for BR (ou for indeterminada), a requisição é bloqueada com 403 e **não** alcança a REST API.
   - **2ª — `Block-SQLi-Lab`**: se a query string casar com o SQL injection match statement, a requisição é bloqueada com 403 e **não** alcança a REST API.
   - Se nenhuma regra casar, a ação padrão **ALLOW** deixa a requisição prosseguir.
5. Quando permitida, a requisição segue para a mesma integração Lambda Proxy e a mesma Lambda.
6. A SQL Injection de teste, vinda do Brasil, é bloqueada pela regra `Block-SQLi-Lab` com **HTTP 403** e **não** executa a Lambda.
![Descrição da imagem](<imagens/imagem%20(8).png>)
---

## Componentes em detalhe

### REST API (`api-waf-lab-sqli`)

- Criada como **REST API** do API Gateway (não HTTP API), com endpoint **Regional**.
- Integração **Lambda Proxy** com a Lambda única.
- Roteamento por `{proxy+}` + `ANY`, mais o recurso raiz `/` + `ANY` (porque `{proxy+}` não captura o caminho raiz).

| Recurso | Método | Destino | Observação |
|---|---|---|---|
| `/` (raiz) | `ANY` | Lambda Proxy | Atende `GET /` (página HTML) |
| `/{proxy+}` | `ANY` | Lambda Proxy | Atende `/health`, `/produto`, `/search`, `/info` e rotas inexistentes (404) |

### Rotas da API

| Rota | Método | Comportamento |
|---|---|---|
| `/` | GET | Página HTML explicativa |
| `/health` | GET | Health check: `{"status":"healthy","project":"AWS WAF Security Lab 03"}` |
| `/produto` | GET | Ecoa o parâmetro `id` (`{"id":"<valor>"}`); sem `id` retorna `{"id":""}` |
| `/search` | GET | Ecoa o parâmetro `q` (`{"q":"<valor>"}`) |
| `/info` | GET | Página HTML explicativa |
| (qualquer outra) | — | HTTP 404 com corpo JSON descritivo |

### Função Lambda (Python)

A função única trata **todas** as rotas por roteamento interno, usando apenas a biblioteca padrão do Python:

- Extrai o método HTTP (`httpMethod`) e o caminho (`path`) do evento Lambda Proxy e despacha para o handler correspondente.
- Normaliza o path de forma defensiva (garante `/` inicial e remove barra final redundante).
- Rotas fora do conjunto definido recebem um **404 controlado**, o que ajuda a diferenciar um erro de rota (404 originado na Lambda) de um bloqueio do WAF (403 originado na Web ACL).
- Grava uma entrada de log por requisição no CloudWatch, contendo `method`, `path`, `requestId` e os parâmetros de query, com truncamento a 256 caracteres e ocultação de campos sensíveis. O registro é **não bloqueante**: falhas no logger não interrompem a resposta.

Trecho representativo do despacho de rotas:

```python
ROUTES = {
    "/": _handle_info,
    "/health": _handle_health,
    "/produto": _handle_produto,
    "/search": _handle_search,
    "/info": _handle_info,
}

def _dispatch(event, path):
    handler = ROUTES.get(path)
    if handler is None:
        return _handle_not_found(event, path)
    return handler(event)
```

A rota `/produto` apenas ecoa o valor recebido, sem qualquer execução de SQL:

```python
def _handle_produto(event):
    produto_id = _get_query_param(event, "id")
    return _json_response(200, {"id": produto_id})
```

### Stages

| Stage | Web ACL associada | Papel |
|---|---|---|
| `sem-waf` | Nenhuma (0 associações) | Grupo de controle |
| `com-waf` | `waf-lab-sqli` (1 associação) | Grupo protegido |

Ambos pertencem à **mesma** REST API e são servidos pela **mesma** Lambda.

### Custom Domains regionais

| Custom Domain | Endpoint | Mapeamento |
|---|---|---|
| `api-sem-waf.DOMINIO` | Regional | stage `sem-waf` |
| `api-com-waf.DOMINIO` | Regional | stage `com-waf` |

Ambos usam o **certificado ACM regional** e são apontados pelos registros Alias do Route 53 na Zona Hospedada existente.

### Web ACL e regras do WAF

- Escopo **Regional (REGIONAL)**, ação padrão **ALLOW**, associada a **exatamente 1 recurso**: o stage `com-waf`.

| Prioridade | Regra | Tipo | Detalhes | Ação |
|---|---|---|---|---|
| 1 | `Block-Fora-do-Brasil` | Geo match | País **BR** com **NOT**, **Source IP** | BLOCK |
| 2 | `Block-SQLi-Lab` | SQL injection match | **Query string**, transformações **URL_DECODE → HTML_ENTITY_DECODE** | BLOCK |

A regra geográfica é avaliada **primeiro** para reduzir a superfície de avaliação: requisições de fora do Brasil são bloqueadas independentemente do conteúdo, e apenas o tráfego do Brasil chega à avaliação de SQLi. País de origem indeterminado é tratado como fora do Brasil (postura conservadora, *fail-closed*).
![Descrição da imagem](<imagens/imagem%20(18).png>)
---

## Decisões de design

### Por que a única diferença é o WAF

Os dois fluxos usam a mesma REST API e a mesma Lambda — mudam apenas o subdomínio, o Custom Domain e o stage de destino. Como não há diferença de código, de integração ou de rota entre os ambientes, **qualquer** diferença de comportamento observada é atribuível exclusivamente ao WAF. O `sem-waf` funciona como grupo de controle e o `com-waf` como grupo protegido.

### Por que `{proxy+}` com `ANY` + roteamento interno

- **Simplicidade de implantação manual**: um único recurso `{proxy+}` com `ANY` encaminha todas as rotas para a Lambda, reduzindo o número de cliques no Console.
- **Fonte única de verdade do roteamento**: todo o roteamento fica na Lambda, garantindo que os dois stages compartilhem exatamente a mesma lógica.
- **Facilidade para 404**: rotas não previstas chegam à Lambda, que responde 404 de forma controlada, permitindo distinguir erro de rota (404) de bloqueio do WAF (403).
- **Raiz `/`**: como `{proxy+}` não captura o caminho raiz, o recurso raiz também recebe `ANY` integrado à mesma Lambda.

### Por que endpoints regionais

Os endpoints da REST API são **regionais** (em vez de edge-optimized) porque a Web ACL do WAF é **regional** e se associa diretamente ao stage regional, e porque o laboratório não usa CloudFront na frente da API. Custom Domains e certificado ACM são regionais, na mesma região dos endpoints.

---

## Implantação

A implantação é **manual**, realizada pelo **Console da AWS em Português (Brasil)**. O laboratório **não** utiliza infraestrutura como código (Terraform, CloudFormation, CDK, SAM) nem automação via AWS CLI. Os scripts existentes servem exclusivamente para testes da API.

O guia completo está em `IMPLANTACAO.md` e segue estas fases:

1. Pré-requisitos e escolha da região.
2. Solicitar o certificado ACM curinga (`*.DOMINIO`).
3. Validar o certificado por DNS e confirmar a emissão.
4. Criar a função Lambda (Python).
5. Publicar o código `lambda_function.py`.
6. Criar a REST API `api-waf-lab-sqli`.
7. Criar os recursos `{proxy+}` e a raiz `/` com método `ANY` (Lambda Proxy).
8. Implantar (deploy) no stage `sem-waf`.
9. Implantar (deploy) no stage `com-waf`.
10. Criar o Custom Domain `api-sem-waf.DOMINIO`.
11. Criar o Custom Domain `api-com-waf.DOMINIO`.
12. Mapear os Custom Domains aos stages.
13. Criar os registros Alias no Route 53.
14. Criar a Web ACL `waf-lab-sqli` com as regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab`.
15. (Referência) Regras e prioridade.
16. Confirmar a associação ao stage `com-waf`.

Os **testes de validação** (comprovação sem WAF x com WAF) ficam em `TESTES.md` e a **exclusão completa dos recursos** (limpeza / teardown) em `EXCLUSAO.md`.

> No Console atual do AWS WAF, o fluxo "Criar pacote de proteção (ACL da Web)" só libera o nome e as regras **depois** de selecionar ao menos um recurso a proteger. Por isso, a associação ao stage `com-waf` é feita já na criação da Web ACL.

---

## Testes e comprovação

Os cenários podem ser executados com `curl` ou pelos scripts do laboratório (Python e PowerShell), que testam o conjunto de requisições por ambiente e retornam código de saída 0 apenas se todos os testes forem aprovados.

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

### Tabela consolidada esperada

| # | Requisição | Stage | HTTP esperado |
|---|---|---|---|
| 1 | `GET /health` | `sem-waf` | 200 |
| 2 | `GET /produto?id=123` | `sem-waf` | 200 |
| 3 | SQL Injection de teste | `sem-waf` | 200 |
| 4 | `GET /health` | `com-waf` | 200 |
| 5 | `GET /produto?id=123` | `com-waf` | 200 |
| 6 | SQL Injection de teste | `com-waf` | 403 (`Block-SQLi-Lab`) |

A única inversão de comportamento entre os stages é a SQL Injection de teste: `200` no `sem-waf` e `403` no `com-waf`.

![Descrição da imagem](<imagens/imagem%20(14).png>)
### Comprovação por CloudWatch

Como os dois stages compartilham a mesma Lambda e o mesmo grupo de logs, a **ausência** de nova entrada de execução e o **incremento zero** da métrica `Invocations` no cenário `com-waf` provam que o WAF interrompeu a requisição **antes** da integração Lambda Proxy. A janela de observação é de no mínimo **60 segundos**.

| Cenário | Stage | HTTP | Nova entrada no log? | Invocations |
|---|---|---|---|---|
| SQL Injection de teste | `sem-waf` | 200 | Sim (com `requestId`) | 1 |
| SQL Injection de teste | `com-waf` (do Brasil) | 403 | Não | 0 |

Como reforço, as **Sampled requests** da Web ACL mostram a regra que casou (`Block-SQLi-Lab` ou `Block-Fora-do-Brasil`), a ação BLOCK, a origem e o código 403.

### Geo-bloqueio (regra `Block-Fora-do-Brasil`)

A origem geográfica é determinada pela AWS a partir do **Source IP** e não deve ser forjada: o teste consiste em executar a requisição de uma rede realmente localizada no país desejado (uma VPN com saída em outro país ou uma instância em outra região servem para simular "fora do Brasil").

| Origem | Requisição | Stage | HTTP | Regra que bloqueia |
|---|---|---|---|---|
| Brasil | `GET /health` | `com-waf` | 200 | — (ALLOW) |
| Brasil | `GET /produto?id=123` | `com-waf` | 200 | — (ALLOW) |
| Brasil | SQL Injection de teste | `com-waf` | 403 | `Block-SQLi-Lab` (prioridade 2) |
| Fora do Brasil | `GET /health` | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Fora do Brasil | `GET /produto?id=123` | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Fora do Brasil | SQL Injection de teste | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Indeterminada | qualquer requisição | `com-waf` | 403 | `Block-Fora-do-Brasil` (tratada como fora do Brasil) |

A comparação evidencia o efeito da **ordem das regras**: do Brasil, a barreira geográfica é transparente e apenas a SQLi é bloqueada; de fora do Brasil, tudo é bloqueado já na regra geográfica, antes da inspeção de SQLi.

### Testes automatizados da lógica da Lambda

Além dos scripts que testam a API real, o diretório `tests/` inclui testes unitários e property-based (pytest/Hypothesis) que validam a lógica pura da Lambda:

- `test_unit_routes.py` — testes unitários das rotas.
- `test_property_routing.py` — propriedades de roteamento.
- `test_property_logging.py` — propriedades de log (truncamento e ocultação de sensíveis).
- `conftest.py` e `requirements-dev.txt` — configuração e dependências de teste.

![Descrição da imagem](<imagens/imagem%20(20).png>)
---

## Segurança

- **Sem vulnerabilidade real:** a rota `/produto` apenas ecoa o parâmetro; não há execução de SQL, conexão com banco nem chamada a serviço de persistência.
- **HTTPS/TLS:** os Custom Domains são servidos com TLS via certificado do ACM.
- **Logs sem dados sensíveis:** a Lambda registra `method`, `path` e `requestId`, trunca valores a 256 caracteres e substitui parâmetros sensíveis (token, senha, credencial, secret, authorization) por `***REDACTED***` antes de gravar.
- **WAF como camada de proteção:** o stage `com-waf` demonstra bloqueio por padrão de SQL Injection e bloqueio geográfico (apenas o Brasil é permitido), com postura *fail-closed* para origem indeterminada.
- **Escopo controlado:** apenas os serviços previstos são usados, sem IaC e sem automação de infraestrutura via AWS CLI.

---

## Custos

Recursos que podem gerar custos: API Gateway (por chamada e transferência), Lambda (por invocação e tempo, geralmente coberto pelo nível gratuito), AWS WAF (por Web ACL, por regra e por requisição inspecionada), Route 53 (por hosted zone e consultas DNS), ACM (certificados públicos por DNS não têm custo de emissão) e CloudWatch (logs, métricas e consultas).

Para manter os custos baixos: use o laboratório por tempo limitado e **exclua todos os recursos ao terminar** (ver `EXCLUSAO.md`), envie um número reduzido de requisições de teste e defina retenção de logs no CloudWatch.

> Valores de preço variam por região e mudam ao longo do tempo. Consulte a página oficial de preços de cada serviço na AWS antes de estimar custos.

---

## Uso responsável

- Execute os scripts **somente contra os endpoints do laboratório** que você mesmo implantou.
- Os scripts enviam um número reduzido de requisições, sem loops contínuos, sem testes de stress, sem flood e sem DDoS.
- O padrão de SQL Injection é usado apenas para acionar a inspeção do WAF; não represente o laboratório como exploração de vulnerabilidade real.
- Não utilize os scripts ou técnicas contra sistemas de terceiros sem autorização explícita.

---

## Conclusão

O laboratório demonstra, com um experimento controlado, o valor de um WAF como camada de proteção na borda. Ao manter a API e a Lambda idênticas entre os dois ambientes e variar apenas a presença do AWS WAF, fica evidente que:

- **Sem WAF**, a requisição maliciosa de teste chega à aplicação e é processada (HTTP 200, `Invocations = 1`).
- **Com WAF**, a mesma requisição é bloqueada na borda (HTTP 403) e nunca chega à Lambda (`Invocations = 0`, sem nova entrada de log).

A comprovação por duas fontes independentes do CloudWatch, somada às Sampled requests da Web ACL, torna o resultado reproduzível e auditável — exatamente o que se espera de uma demonstração de segurança didática.

---

## Referências do projeto

- `README.md` — visão geral do laboratório.
- `ARQUITETURA.md` — arquitetura de rede e componentes.
- `IMPLANTACAO.md` — guia de implantação manual pelo Console AWS (pt-BR).
- `TESTES.md` — guia de testes de validação (sem WAF x com WAF, CloudWatch, Sampled requests, geo-bloqueio).
- `EXCLUSAO.md` — guia de exclusão / teardown completo dos recursos.
- `lambda/lambda_function.py` — função Lambda com roteamento interno.
- `tests/` — scripts de teste da API (Python e PowerShell) e testes automatizados (pytest/Hypothesis).
