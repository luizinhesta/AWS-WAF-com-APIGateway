# AWS WAF Security Lab 03 — Proteção contra SQL Injection com API Gateway REST + AWS Lambda

Laboratório educacional que demonstra, de forma prática e didática, a diferença de comportamento entre uma API **sem AWS WAF** e a **mesma** API **com AWS WAF**, usando uma requisição com padrão de SQL Injection **apenas para acionar a inspeção do WAF**.

> **Importante:** este laboratório **não** contém vulnerabilidade real, **não** usa banco de dados e **não** executa SQL. A rota `/produto` apenas **ecoa** o parâmetro recebido. O padrão de SQL Injection é usado exclusivamente como gatilho de inspeção do WAF.

---

## Objetivo do laboratório

O laboratório expõe **dois ambientes** construídos sobre a **mesma REST API** e a **mesma função Lambda**:

- **Ambiente SEM WAF** — stage `sem-waf`, sem nenhuma Web ACL associada. Funciona como **grupo de controle**.
- **Ambiente COM WAF** — stage `com-waf`, associado à Web ACL `waf-lab-sqli`. Funciona como **grupo protegido**.

Como os dois stages compartilham a **mesma** API e a **mesma** Lambda, a **única diferença observável** entre eles é a presença do **AWS WAF** no stage `com-waf`. Assim, qualquer diferença de comportamento entre os dois subdomínios é atribuível **exclusivamente** ao WAF — que é o ponto central do laboratório.

### Comparação entre os ambientes

A requisição de teste de SQL Injection é `GET /produto?id=1' OR '1'='1` (usada só para inspeção, sem vulnerabilidade real).

| Requisição | Ambiente | Resultado HTTP | Chega à Lambda? | Invocations (CloudWatch) |
|---|---|---|---|---|
| SQL Injection de teste | `sem-waf` | **200** (id ecoado) | Sim (nova entrada de log com `requestId`) | 1 |
| SQL Injection de teste | `com-waf` (origem no Brasil) | **403** (bloqueado pelo WAF) | Não | 0 |
| Requisição de origem fora do Brasil | `com-waf` | **403** (bloqueado pela regra geográfica) | Não | 0 |

A comprovação de que o WAF bloqueia **antes** da integração Lambda Proxy apoia-se em duas fontes independentes do **CloudWatch** para a mesma Lambda: o **grupo de logs** `/aws/lambda/{nome-da-funcao}` (nova entrada por execução) e a **métrica `Invocations`** (namespace `AWS/Lambda`). No ambiente `com-waf`, a ausência de nova entrada e o incremento zero da métrica provam que o bloqueio ocorreu no WAF, e não na Lambda.

---

## Serviços AWS utilizados

O laboratório utiliza **somente** os seguintes serviços:

- **Route 53** — hosted zone existente do domínio; registros Alias para os subdomínios.
- **ACM (AWS Certificate Manager)** — certificado TLS regional para os Custom Domains (pode ser curinga `*.DOMINIO`).
- **API Gateway** — 1 REST API (REST, não HTTP), com integração Lambda Proxy.
- **Lambda** — 1 função em Python que trata todas as rotas via roteamento interno.
- **AWS WAF** — 1 Web ACL regional (`waf-lab-sqli`) com 2 regras.
- **CloudWatch** — grupo de logs da Lambda e métrica `Invocations` para comprovar chegada e bloqueio.

> Este laboratório **não** usa DynamoDB, RDS, Aurora, EC2, ECS, CloudFront, ALB, NLB, Cognito, SQS, SNS, Bot Control, Fraud Control nem Marketplace Managed Rules. Os endpoints são **regionais** (sem CloudFront na frente da API).

---

## Arquitetura (fixa)

A arquitetura é fixa e composta por:

- **1 REST API** — `api-waf-lab-sqli` (REST API do API Gateway, **não** HTTP API), integração **Lambda Proxy**, roteamento por `{proxy+}` + `ANY` (mais o recurso raiz `/` com `ANY`).
- **1 Lambda** — `lambda/lambda_function.py`, roteamento interno de todas as rotas.
- **2 stages** — `sem-waf` (sem Web ACL) e `com-waf` (com Web ACL), sobre a mesma API e a mesma Lambda.
- **2 Custom Domains regionais** — `api-sem-waf.DOMINIO` (mapeado ao stage `sem-waf`) e `api-com-waf.DOMINIO` (mapeado ao stage `com-waf`).
- **1 Web ACL regional** — `waf-lab-sqli`, escopo Regional (REGIONAL), ação padrão **ALLOW**, associada **somente** ao stage `com-waf`.
- **2 regras** avaliadas em ordem de prioridade:
  1. **`Block-Fora-do-Brasil`** (prioridade 1) — correspondência geográfica com o país BR e lógica de negação (NOT); ação **BLOCK**.
  2. **`Block-SQLi-Lab`** (prioridade 2) — SQL injection match statement na query string; ação **BLOCK**.

Sem banco de dados, sem CloudFront. A rota `/produto` **apenas ecoa** o parâmetro recebido (sem vulnerabilidade real, sem SQL, sem banco).

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

Para os detalhes de fluxo de rede e das decisões de arquitetura, veja [`ARQUITETURA.md`](./ARQUITETURA.md).

### Rotas da API

| Rota | Método | Comportamento |
|---|---|---|
| `/` | GET | Página HTML explicativa |
| `/health` | GET | Health check: `{"status":"healthy","project":"AWS WAF Security Lab 03"}` |
| `/produto` | GET | Ecoa o parâmetro `id` (`{"id":"<valor>"}`); sem `id` retorna `{"id":""}` |
| `/search` | GET | Ecoa o parâmetro `q` (`{"q":"<valor>"}`) |
| `/info` | GET | Página HTML explicativa |
| (qualquer outra) | — | HTTP 404 com corpo JSON descritivo |

---

## Estrutura de arquivos

Todos os arquivos ficam sob o diretório raiz `aws-waf-lab-03-sqli/`:

```
aws-waf-lab-03-sqli/
├── lambda/
│   └── lambda_function.py         # Função Lambda (Python) — roteamento interno de todas as rotas
├── tests/
│   ├── test-sqli.py               # Script de teste da API em Python (sem-waf / com-waf)
│   ├── test-sqli.ps1              # Script de teste da API em PowerShell (mesmo contrato do Python)
│   ├── test_property_logging.py   # Testes automatizados (pytest/hypothesis) — propriedades de log
│   ├── test_property_routing.py   # Testes automatizados (pytest/hypothesis) — propriedades de roteamento
│   ├── test_unit_routes.py        # Testes unitários das rotas da Lambda
│   ├── conftest.py                # Configuração para importar lambda_function nos testes
│   └── requirements-dev.txt       # Dependências de teste (pytest, hypothesis)
├── README.md                      # Este documento — visão geral do laboratório
├── ARQUITETURA.md                 # Arquitetura: fluxo de rede e componentes
└── IMPLANTACAO.md                 # Guia passo a passo de implantação manual pelo Console AWS (pt-BR, inclui a fase de testes)
```

- **`lambda/lambda_function.py`** — código executado nos dois stages, idêntico para ambos.
- **`tests/test-sqli.py`** e **`tests/test-sqli.ps1`** — scripts que testam a API real (Python e PowerShell) contra os stages `sem-waf` e `com-waf`, incluindo o teste geográfico.
- **`tests/` (testes automatizados com pytest/Hypothesis)** — `test_property_logging.py`, `test_property_routing.py`, `test_unit_routes.py`, `conftest.py` e `requirements-dev.txt` validam a lógica pura da Lambda (unitários e property-based).

---

## Implantação

A implantação é **manual**, realizada pelo **Console da AWS em Português (Brasil)**.

Este laboratório **não** utiliza ferramentas de infraestrutura como código (**Terraform, CloudFormation, CDK, SAM**) nem automação de infraestrutura via **AWS CLI**. Os scripts existentes servem **exclusivamente para testes da API**.

O passo a passo completo (certificado ACM, REST API, stages, Custom Domains, registros Route 53, Web ACL e regras do WAF), com nomes de menus em pt-BR e o original em inglês entre parênteses quando útil, está em [`IMPLANTACAO.md`](./IMPLANTACAO.md), que inclui a **Fase 17 — Testes de validação** com os cenários de comprovação (sem WAF x com WAF, CloudWatch e Sampled requests do WAF).

---

## Custos

Este laboratório utiliza recursos que podem gerar custos na sua conta AWS. Pontos de atenção:

- **API Gateway (REST API)** — cobrança por número de chamadas de API e por transferência de dados.
- **AWS Lambda** — cobrança por invocação e por tempo de execução (nível gratuito costuma cobrir o uso do laboratório).
- **AWS WAF** — cobrança mensal por Web ACL, por regra configurada e por requisição inspecionada.
- **Route 53** — cobrança mensal por hosted zone e por consultas DNS.
- **ACM** — certificados públicos validados por DNS **não** têm custo adicional de emissão.
- **CloudWatch** — cobrança por armazenamento de logs, métricas e consultas.

Recomendações para manter os custos baixos:

- Use o laboratório por tempo limitado e **exclua todos os recursos ao terminar**, seguindo a fase de exclusão descrita em [`IMPLANTACAO.md`](./IMPLANTACAO.md).
- Envie um **número reduzido de requisições** de teste (os scripts já seguem esse princípio).
- Defina retenção de logs no CloudWatch para evitar acúmulo indefinido.

> Valores de preço variam por região e mudam ao longo do tempo. Consulte a página oficial de preços de cada serviço na AWS antes de estimar custos.

---

## Segurança

- **Sem vulnerabilidade real:** a rota `/produto` apenas ecoa o parâmetro; não há execução de SQL, conexão com banco de dados nem chamada a serviço externo de persistência.
- **HTTPS/TLS:** os Custom Domains são servidos com TLS via certificado do ACM.
- **Logs sem dados sensíveis:** a Lambda registra `method`, `path` e `requestId`, e trunca cada valor de parâmetro a no máximo 256 caracteres. Parâmetros cujo nome corresponda a campos sensíveis (token, senha, credencial, secret, autorização) têm o valor substituído por um marcador de ocultação (`***REDACTED***`) antes de serem registrados. Cabeçalhos de autorização, tokens, senhas, credenciais e secrets nunca são gravados em texto claro.
- **WAF como camada de proteção:** o stage `com-waf` demonstra bloqueio por padrão de SQL Injection e bloqueio geográfico (apenas o Brasil é permitido). País de origem indeterminado é tratado como fora do Brasil (postura conservadora, fail-closed).
- **Escopo controlado:** apenas os serviços previstos são usados, sem infraestrutura como código e sem automação de infraestrutura via AWS CLI.

---

## Uso responsável

Os testes deste laboratório devem permanecer **éticos e restritos ao próprio laboratório**:

- Execute os scripts **somente contra os endpoints do laboratório** que você mesmo implantou.
- Os scripts enviam um **número reduzido de requisições**, **sem loops de repetição contínua**, **sem testes de stress**, **sem flood** e **sem DDoS**.
- O padrão de SQL Injection é usado **apenas para acionar a inspeção do WAF**; não represente nem trate este laboratório como uma exploração de vulnerabilidade real.
- Não utilize os scripts ou técnicas deste laboratório contra sistemas de terceiros sem autorização explícita.

---

## Documentação relacionada

- [`ARQUITETURA.md`](./ARQUITETURA.md) — arquitetura de rede e componentes.
- [`IMPLANTACAO.md`](./IMPLANTACAO.md) — guia de implantação manual pelo Console AWS (pt-BR).
