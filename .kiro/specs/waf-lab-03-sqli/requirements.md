# Requisitos — Lab 03: Proteção contra SQL Injection (API Gateway REST + Lambda)

## Introdução

Este laboratório educacional demonstra a diferença entre uma API Serverless **sem AWS WAF** e **com AWS WAF**, usando **SQL Injection (SQLi)** como teste. Uma única REST API com integração Lambda é exposta por dois stages (e dois Custom Domains): um sem proteção e um protegido por uma Web ACL regional com uma regra de SQLi. O objetivo é comprovar que uma requisição com padrão de SQLi chega à Lambda quando não há WAF e é bloqueada (HTTP 403) antes da Lambda quando há WAF — evidenciado pela ausência de execução nos CloudWatch Logs e na métrica Invocations.

Não há banco de dados neste laboratório.

## Glossário

- **SQL Injection:** manipulação de entrada para alterar comandos SQL. Aqui é apenas string de teste; não há banco nem execução de SQL.
- **Stage:** versão publicada da REST API com URL própria.
- **Custom Domain:** domínio personalizado do API Gateway mapeado a um stage.

## Requisitos

### Requisito 1 — Dois endpoints com a mesma API

**User Story:** Como estudante, quero dois stages da mesma API, para que a única diferença seja o WAF.

#### Critérios de Aceitação
1. O sistema DEVE ter uma REST API com dois stages: `sem-waf` e `com-waf`.
2. Os dois stages DEVEM integrar com a **mesma** função Lambda.
3. Cada stage DEVE ter um Custom Domain próprio (`api-sem-waf`, `api-com-waf`).

### Requisito 2 — Aplicação Lambda sem banco

**User Story:** Como estudante, quero uma Lambda simples que ecoa parâmetros, para testar o WAF sem banco de dados.

#### Critérios de Aceitação
1. A Lambda DEVE responder `GET /health` com `{"status":"healthy","project":"AWS WAF Security Lab 03"}` e HTTP 200.
2. A Lambda DEVE responder `GET /produto?id=123` ecoando o `id`, sem consultar banco.
3. A Lambda DEVE oferecer uma rota `/info` (ou `/`) com uma página HTML explicando o laboratório.
4. A Lambda NÃO DEVE usar banco de dados nem executar SQL.
5. Os logs DEVEM registrar apenas dados seguros (method, path, requestId, parâmetro recebido) e NUNCA credenciais, tokens ou segredos.

### Requisito 3 — HTTPS e domínio próprio

#### Critérios de Aceitação
1. O sistema DEVE usar um certificado ACM na **mesma região** da API (Custom Domain Regional), validado por DNS.
2. O Route 53 DEVE ter registros Alias apontando cada subdomínio para seu Custom Domain.

### Requisito 4 — Regra de WAF para SQL Injection

#### Critérios de Aceitação
1. O sistema DEVE ter uma Web ACL **regional** chamada `waf-lab-sqli`.
2. A Web ACL DEVE conter uma única regra `Block-SQLi-Lab` do tipo **SQLi match statement**.
3. A regra DEVE inspecionar a query string (todos os parâmetros de consulta) com transformação **URL decode**.
4. A ação DEVE ser **Block** e a ação padrão DEVE ser **Allow**.
5. A Web ACL DEVE ser associada **somente** ao stage `com-waf`.
6. O sistema NÃO DEVE usar Bot Control, Fraud Control, Marketplace Rules ou Managed Rule Groups desnecessários.

### Requisito 5 — Comportamento comprovável (Lambda não executa)

#### Critérios de Aceitação
1. QUANDO `/health` ou `/produto?id=123` é chamado em qualquer stage ENTÃO o sistema DEVE responder **200**.
2. QUANDO uma requisição de SQLi é enviada ao stage sem WAF ENTÃO a Lambda DEVE executar (log + `Invocations` incrementa) e responder 200.
3. QUANDO uma requisição de SQLi é enviada ao stage com WAF ENTÃO o sistema DEVE responder **403** e a Lambda **não** DEVE executar (sem log, sem incremento de `Invocations`).
4. O bloqueio DEVE ser visível no CloudWatch (WAF: `BlockedRequests`; API Gateway: `4XXError`; Lambda: `Invocations`).

### Requisito 6 — Scripts de teste controlado

#### Critérios de Aceitação
1. O sistema DEVE fornecer `test-sqli.py` e `test-sqli.ps1`.
2. Os scripts DEVEM receber as URLs sem WAF e com WAF.
3. Os scripts DEVEM executar `/health`, `/produto?id=123` e um SQLi controlado por endpoint (sem threads, flood ou DDoS).
4. Os scripts DEVEM aplicar **URL encoding** ao payload e tratar **403** como resultado esperado.

### Requisito 7 — Segurança, custo e exclusão

#### Critérios de Aceitação
1. Os testes DEVEM ser executados somente contra os próprios endpoints do laboratório.
2. O laboratório NÃO DEVE criar banco vulnerável, executar SQL real, DDoS, stress ou grande volume de requisições.
3. O laboratório DEVE usar 1 Web ACL + 1 regra + poucas requisições.
4. A documentação DEVE alertar que o AWS WAF não é gratuito de forma permanente e fornecer procedimento de exclusão.
