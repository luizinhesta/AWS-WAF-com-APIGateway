# Arquitetura — AWS WAF Security Lab 03 (SQL Injection)

Este documento descreve a arquitetura do laboratório educacional **AWS WAF Security Lab — Projeto 03: Proteção contra SQL Injection com API Gateway REST + AWS Lambda**. O objetivo é demonstrar, de forma prática, a diferença de comportamento entre uma API **sem AWS WAF** e a **mesma** API **com AWS WAF** diante de uma requisição com padrão de SQL Injection usada apenas para acionar a inspeção.

O laboratório **não** contém vulnerabilidade real, **não** usa banco de dados e **não** executa SQL: a rota `/produto` apenas ecoa o parâmetro recebido. A infraestrutura é criada **manualmente** pelo Console da AWS em Português (Brasil), sem infraestrutura como código.

Serviços utilizados: **Route 53, ACM, API Gateway, Lambda, AWS WAF e CloudWatch**.

## Visão geral do fluxo (Internet → CloudWatch)

O laboratório expõe **dois subdomínios**, cada um mapeado a um **stage** diferente da **mesma** REST API. A Web ACL do WAF está associada **somente** ao stage `com-waf`. O fluxo completo é:

**Internet → Route 53 → subdomínios (`api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO`) → Custom Domains regionais do API Gateway → stage → (Web ACL só no `com-waf`) → integração Lambda Proxy → Lambda → CloudWatch.**

```
                                    Internet
                                       |
                          +------------+------------+
                          |                         |
              api-sem-waf.DOMINIO         api-com-waf.DOMINIO
                          |                         |
                     Route 53                   Route 53
                (Alias A/AAAA regional)    (Alias A/AAAA regional)
                          |                         |
              Custom Domain (regional)   Custom Domain (regional)
              Certificado ACM (regional) Certificado ACM (regional)
                          |                         |
                 API mapping -> stage      API mapping -> stage
                          |                         |
                 +--------v---------+      +---------v--------+
                 | REST API (mesma) |      | REST API (mesma) |
                 |  stage: sem-waf  |      |  stage: com-waf  |
                 +--------+---------+      +---------+--------+
                          |                          |
                          |                 +--------v---------+
                          |                 |  Web ACL (WAF)   |
                          |                 |  waf-lab-sqli    |
                          |                 |  1) Block-Fora-  |
                          |                 |     do-Brasil    |
                          |                 |  2) Block-SQLi-  |
                          |                 |     Lab          |
                          |                 |  default: ALLOW  |
                          |                 +--------+---------+
                          |                          | (se ALLOW)
                          +------------+-------------+
                                       |
                          Integração Lambda Proxy
                                       |
                          +------------v------------+
                          |   Lambda (Python)       |
                          |  lambda_function.py     |
                          |  roteamento interno     |
                          +------------+------------+
                                       |
                              CloudWatch Logs
                          /aws/lambda/{funcao}
                          + métrica Invocations
```

### Fluxo SEM WAF (stage `sem-waf`)

1. O cliente resolve `api-sem-waf.DOMINIO` pelo Route 53 (registro Alias para o Custom Domain regional).
2. A requisição chega ao Custom Domain `api-sem-waf.DOMINIO`, servido com TLS pelo Certificado ACM regional.
3. O API mapping direciona para o stage `sem-waf` da REST API.
4. Como o stage `sem-waf` **não** possui Web ACL associada, a requisição segue direto para a integração Lambda Proxy.
5. A Lambda executa, grava log no CloudWatch e incrementa a métrica `Invocations`.
6. A requisição de SQL Injection de teste (`GET /produto?id=1' OR '1'='1`) recebe **HTTP 200** com o `id` ecoado.

### Fluxo COM WAF (stage `com-waf`)

1. O cliente resolve `api-com-waf.DOMINIO` pelo Route 53 (registro Alias para o Custom Domain regional).
2. A requisição chega ao Custom Domain `api-com-waf.DOMINIO`, servido com TLS pelo Certificado ACM regional.
3. O API mapping direciona para o stage `com-waf`, que possui a **Web ACL `waf-lab-sqli`** associada.
4. A Web ACL avalia as regras na ordem de prioridade:
   - **1ª — `Block-Fora-do-Brasil`**: se a origem não for BR (ou for indeterminada), a requisição é bloqueada com 403 e **não** alcança a REST API.
   - **2ª — `Block-SQLi-Lab`**: se a query string casar com o SQL injection match statement, a requisição é bloqueada com 403 e **não** alcança a REST API.
   - Se nenhuma regra casar, a ação padrão **ALLOW** deixa a requisição prosseguir.
5. Quando permitida, a requisição segue para a mesma integração Lambda Proxy e a mesma Lambda do fluxo sem WAF.
6. A requisição de SQL Injection de teste, vinda do Brasil, é bloqueada pela regra `Block-SQLi-Lab` com **HTTP 403** e **não** executa a Lambda.

## Componentes

A arquitetura é fixa e composta por: **1 REST API, 1 Lambda, 2 stages, 2 Custom Domains regionais, 1 Web ACL regional e 2 regras de WAF.**

### 1. REST API (`api-waf-lab-sqli`)

- Criada como **REST API** do API Gateway (não HTTP API).
- Tipo de endpoint: **Regional** (compatível com Custom Domains regionais e Web ACL regional).
- Integração: **Lambda Proxy** com a Lambda única.
- Roteia as rotas `/health`, `/produto`, `/search`, `/info` e `/` para a Lambda.

### 2. Lambda (`lambda/lambda_function.py`, Python)

- Função **única** que trata **todas** as rotas via roteamento interno.
- Extrai o método HTTP (`httpMethod`) e o caminho (`path`) do evento Lambda Proxy e despacha para o handler correspondente.
- Rotas atendidas: `GET /health`, `GET /produto`, `GET /search`, `GET /` e `GET /info`; qualquer outra rota resulta em **404** controlado.
- Grava log no CloudWatch (método, caminho e `requestId`) e nunca executa SQL, abre banco de dados ou chama serviço de persistência.

### 3. Stages (`sem-waf` e `com-waf`)

| Stage | Web ACL associada | Papel |
|---|---|---|
| `sem-waf` | Nenhuma (0 associações) | Grupo de controle |
| `com-waf` | `waf-lab-sqli` (1 associação) | Grupo protegido |

Ambos os stages pertencem à **mesma** REST API e são servidos pela **mesma** Lambda.

### 4. Custom Domains regionais

| Custom Domain | Endpoint | Mapeamento |
|---|---|---|
| `api-sem-waf.DOMINIO` | Regional | stage `sem-waf` |
| `api-com-waf.DOMINIO` | Regional | stage `com-waf` |

Ambos usam o **Certificado ACM regional** e são apontados pelos registros Alias do Route 53 na Zona Hospedada existente.

### 5. Web ACL regional (`waf-lab-sqli`)

- Escopo **Regional (REGIONAL)**.
- Ação padrão **ALLOW**.
- Associada a **exatamente 1 recurso**: o stage `com-waf` (0 associações ao stage `sem-waf`).

### 6. Regras de WAF

| Prioridade | Regra | Tipo | Ação |
|---|---|---|---|
| 1 | `Block-Fora-do-Brasil` | Geo match (país BR com NOT, Source IP) | BLOCK |
| 2 | `Block-SQLi-Lab` | SQL injection match statement (query string/argumentos) | BLOCK |

- **`Block-Fora-do-Brasil` (prioridade 1)**: correspondência geográfica com o país **BR** (ISO 3166-1 alpha-2) usando lógica de **negação (NOT)** — casa somente quando a origem é diferente de BR. Usa o **endereço de origem (Source IP address)** e trata país indeterminado como fora do Brasil (postura fail-closed). Ação **BLOCK**.
- **`Block-SQLi-Lab` (prioridade 2)**: **SQL injection match statement** inspecionando a **query string** e os **argumentos** da requisição, com transformações de texto na ordem **URL_DECODE** e depois **HTML_ENTITY_DECODE**. Ação **BLOCK**.

A regra geográfica é avaliada **primeiro** para reduzir a superfície de avaliação: requisições de fora do Brasil são bloqueadas independentemente do conteúdo, e apenas o tráfego do Brasil chega à avaliação de SQLi. Isso torna o comportamento **determinístico**.

## Por que a única diferença é o WAF

Os dois fluxos usam **a mesma REST API** e **a mesma Lambda** — mudam apenas o subdomínio, o Custom Domain e o stage de destino. O stage `sem-waf` permanece **sem** qualquer associação de Web ACL, enquanto o stage `com-waf` está associado à Web ACL `waf-lab-sqli`.

Como não há diferença de código, de lógica de integração ou de configuração de rota entre os ambientes, **qualquer** diferença de comportamento observada entre os dois subdomínios é atribuível **exclusivamente** ao WAF. O `sem-waf` funciona como **grupo de controle** e o `com-waf` como **grupo protegido**. Esse é o ponto central e didático do laboratório.

## Escolha de `{proxy+}` com método `ANY` + roteamento interno na Lambda

O laboratório adota o recurso **`{proxy+}` com método `ANY`** combinado ao roteamento interno na Lambda, em vez de criar cada recurso e método explicitamente no API Gateway. Justificativa:

- **Simplicidade de implantação manual**: com `{proxy+}` cria-se um único recurso `ANY` que encaminha **todas** as rotas para a Lambda, reduzindo drasticamente o número de cliques no Console para criar recursos e métodos.
- **Fonte única de verdade do roteamento**: todo o roteamento fica na Lambda (`lambda_function.py`), garantindo que os dois stages compartilhem exatamente a mesma lógica de rotas.
- **Facilidade para 404**: rotas não previstas chegam à Lambda, que responde 404 de forma controlada, permitindo diferenciar um **erro de rota** (404 originado pela Lambda) de um **bloqueio do WAF** (403 originado pela Web ACL antes da integração).
- **Observação sobre a raiz `/`**: como `{proxy+}` não captura o caminho raiz, o recurso raiz **também** recebe o método `ANY` integrado à mesma Lambda, garantindo o atendimento de `GET /`.

### Recursos e métodos

| Recurso | Método | Destino | Observação |
|---|---|---|---|
| `/` (raiz) | `ANY` | Lambda Proxy | Atende `GET /` (página HTML) |
| `/{proxy+}` | `ANY` | Lambda Proxy | Atende `/health`, `/produto`, `/search`, `/info` e rotas inexistentes (404) |

## Comprovação por CloudWatch

A comprovação de que o WAF **bloqueia antes da integração** apoia-se em duas fontes independentes do CloudWatch, ambas relativas à **mesma** Lambda:

- **Grupo de logs** `/aws/lambda/{nome-da-funcao}`: cada execução da Lambda grava uma entrada com método, caminho e `requestId`. Se a Lambda executar, há uma nova entrada; se não executar, não há entrada.
- **Métrica `Invocations`** (namespace `AWS/Lambda`): incrementa em 1 a cada execução da função.

O raciocínio de comprovação:

| Cenário | Stage | Resultado HTTP | Nova entrada no log? | Invocations |
|---|---|---|---|---|
| SQL Injection de teste | `sem-waf` | 200 | Sim (com `requestId`) | 1 |
| SQL Injection de teste | `com-waf` (do Brasil) | 403 | Não | 0 |

Como os dois stages compartilham a mesma Lambda e o mesmo grupo de logs, a **ausência** de nova entrada de execução e o **incremento zero** da métrica no cenário `com-waf` provam que o WAF interrompeu a requisição **antes** da integração Lambda Proxy — ou seja, o bloqueio ocorre no WAF, e não na Lambda. A janela de observação é de no mínimo **60 segundos**.

Como reforço adicional, as **Solicitações de amostra (Sampled requests)** da Web ACL mostram a regra que casou, a ação BLOCK, a origem e o código 403.

## Endpoints regionais e certificado ACM

- Os endpoints da REST API são **regionais** (em vez de edge-optimized), porque a Web ACL do WAF é **regional (REGIONAL)** e associa-se diretamente ao stage regional, e porque o laboratório **não** utiliza CloudFront na frente da API.
- Os **Custom Domains** são regionais, na mesma região dos endpoints.
- O **Certificado ACM** é **regional**, emitido na mesma região dos endpoints, e cobre `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO` (podendo ser um certificado curinga `*.DOMINIO`), com validação por DNS na Zona Hospedada do Route 53.
