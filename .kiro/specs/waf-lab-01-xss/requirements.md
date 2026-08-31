# Requisitos — Lab 01: Proteção contra XSS (CloudFront + S3)

## Introdução

Este laboratório educacional demonstra, de forma prática e controlada, a diferença entre uma aplicação **sem AWS WAF** e uma aplicação **com AWS WAF**, usando **Cross-Site Scripting (XSS)** como teste. Dois endpoints servem o mesmo site estático (S3 privado via CloudFront): um sem proteção e um protegido por uma Web ACL com uma regra de XSS. O objetivo é comprovar que o endpoint protegido bloqueia (HTTP 403) uma requisição com padrão de XSS na query string, enquanto o não protegido a deixa passar.

O laboratório usa a menor quantidade possível de recursos e evita recursos premium. Todos os testes são executados exclusivamente contra os próprios endpoints do laboratório.

## Glossário

- **XSS (Cross-Site Scripting):** padrão de ataque que injeta scripts via entrada do usuário. Aqui é usado apenas como string de teste, sem execução real.
- **Web ACL / pacote de proteção:** conjunto de regras do AWS WAF associado a um recurso.
- **OAC (Origin Access Control):** mecanismo que permite ao CloudFront acessar um bucket S3 privado.

## Requisitos

### Requisito 1 — Dois endpoints com o mesmo conteúdo

**User Story:** Como estudante do laboratório, quero dois endpoints servindo o mesmo site, para que a única diferença entre eles seja a presença do WAF.

#### Critérios de Aceitação
1. QUANDO o site é publicado ENTÃO o sistema DEVE servir o mesmo conteúdo (`index.html`, `style.css`, `script.js`) em ambos os endpoints.
2. O sistema DEVE expor um endpoint **sem WAF** (`site-sem-waf`) e um endpoint **com WAF** (`site-com-waf`).
3. Ambos os endpoints DEVEM usar a **mesma origem** (um único bucket S3 privado).

### Requisito 2 — Origem privada e segura (S3 + OAC)

**User Story:** Como responsável pelo lab, quero que o bucket S3 seja privado, para que o conteúdo só seja acessível através do CloudFront.

#### Critérios de Aceitação
1. O bucket S3 DEVE ter **Block Public Access** ativado.
2. O acesso ao bucket DEVE ocorrer somente via **OAC** do CloudFront.
3. A **bucket policy** DEVE autorizar apenas as duas distribuições CloudFront do laboratório.
4. O sistema NÃO DEVE usar o endpoint público de website do S3.

### Requisito 3 — HTTPS e domínio próprio

**User Story:** Como usuário, quero acessar os endpoints por HTTPS com domínio próprio, para uma experiência realista.

#### Critérios de Aceitação
1. O sistema DEVE usar um certificado ACM em **us-east-1** (exigência do CloudFront).
2. A validação do certificado DEVE ser por **DNS** via Route 53.
3. QUANDO uma requisição chega por HTTP ENTÃO o CloudFront DEVE redirecionar para HTTPS.
4. O Route 53 DEVE ter registros Alias apontando cada subdomínio para sua distribuição.

### Requisito 4 — Regra de WAF para XSS

**User Story:** Como estudante, quero uma regra de WAF que detecte XSS, para bloquear a requisição maliciosa antes da origem.

#### Critérios de Aceitação
1. O sistema DEVE ter uma Web ACL de escopo **CloudFront (global)** chamada `waf-lab-xss`.
2. A Web ACL DEVE conter uma única regra `Block-XSS-Lab` do tipo **XSS match statement**.
3. A regra DEVE inspecionar a **query string** (todos os parâmetros de consulta) com transformação de texto **URL decode**.
4. A ação da regra DEVE ser **Block** e a ação padrão da Web ACL DEVE ser **Allow**.
5. A Web ACL DEVE ser associada **somente** à distribuição com WAF.
6. O sistema NÃO DEVE usar Bot Control, Fraud Control, CAPTCHA pago, Marketplace Rules ou Managed Rule Groups.

### Requisito 5 — Comportamento de bloqueio comprovável

**User Story:** Como estudante, quero comprovar o bloqueio, para validar que o WAF funciona.

#### Critérios de Aceitação
1. QUANDO uma requisição normal é enviada ao endpoint sem WAF ENTÃO o sistema DEVE responder **200**.
2. QUANDO uma requisição normal é enviada ao endpoint com WAF ENTÃO o sistema DEVE responder **200**.
3. QUANDO uma requisição com padrão de XSS é enviada ao endpoint sem WAF ENTÃO ela DEVE passar (tende a **200**).
4. QUANDO uma requisição com padrão de XSS é enviada ao endpoint com WAF ENTÃO o sistema DEVE responder **403**.
5. O bloqueio DEVE ser visível no CloudWatch (`BlockedRequests`) e nas Sampled Requests, com a regra `Block-XSS-Lab` como responsável.

### Requisito 6 — Scripts de teste controlado

**User Story:** Como estudante, quero scripts de teste, para rodar a validação de forma padronizada.

#### Critérios de Aceitação
1. O sistema DEVE fornecer `test-xss.py` (Python) e `test-xss.ps1` (PowerShell).
2. Os scripts DEVEM receber as URLs sem WAF e com WAF como parâmetros.
3. Os scripts DEVEM aplicar **URL encoding** ao payload de XSS.
4. Os scripts DEVEM executar apenas uma requisição normal e uma de XSS por endpoint (sem threads, flood ou DDoS).
5. Os scripts DEVEM tratar **403** como resultado esperado (não como erro).

### Requisito 7 — Segurança e uso responsável

**User Story:** Como responsável, quero garantir uso ético, para não causar dano.

#### Critérios de Aceitação
1. Os testes DEVEM ser executados somente contra os endpoints do próprio laboratório.
2. O laboratório NÃO DEVE executar ataques contra terceiros, DDoS, stress test ou grande volume de requisições.
3. Nenhum script DEVE ser efetivamente executado no servidor — o XSS é apenas uma string de teste.

### Requisito 8 — Custo controlado e exclusão

**User Story:** Como responsável pelo custo, quero remover tudo ao final, para evitar cobranças recorrentes.

#### Critérios de Aceitação
1. O laboratório DEVE usar 1 Web ACL + 1 regra + poucas requisições.
2. A documentação DEVE deixar claro que o AWS WAF não é gratuito de forma permanente.
3. A documentação DEVE fornecer um procedimento de exclusão de todos os recursos.
