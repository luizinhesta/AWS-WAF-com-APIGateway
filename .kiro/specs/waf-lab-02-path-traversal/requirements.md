# Requisitos — Lab 02: Proteção contra Path Traversal / LFI (ALB + EC2 Linux)

## Introdução

Este laboratório educacional demonstra a diferença entre uma aplicação **sem AWS WAF** e **com AWS WAF**, usando **Path Traversal / Local File Inclusion (LFI)** como teste. Dois Application Load Balancers apontam para a mesma instância EC2 (Ubuntu + Nginx) via Target Groups: um sem proteção e um protegido por uma Web ACL regional com uma regra de Path Traversal. O objetivo é comprovar que uma requisição com padrão `../` chega ao Nginx quando não há WAF e é bloqueada (HTTP 403) antes da aplicação quando há WAF — evidenciado pela ausência da requisição no `access.log` do Nginx.

## Glossário

- **Path Traversal / LFI:** tentativa de usar `../` para acessar arquivos fora do diretório esperado. Aqui é apenas string de teste, sem leitura real de arquivos.
- **ALB:** Application Load Balancer.
- **Target Group:** grupo de destinos (a EC2) com health check.
- **SSM Session Manager:** administração da EC2 sem SSH aberto.

## Requisitos

### Requisito 1 — Dois endpoints com a mesma aplicação

**User Story:** Como estudante, quero dois ALBs apontando para a mesma EC2, para que a única diferença seja o WAF.

#### Critérios de Aceitação
1. O sistema DEVE expor um endpoint **sem WAF** (`alb-sem-waf`) e um **com WAF** (`alb-com-waf`).
2. Os dois ALBs DEVEM encaminhar para a **mesma** instância EC2 via Target Groups.
3. A aplicação DEVE servir o mesmo conteúdo em ambos os caminhos.

### Requisito 2 — Rede (VPC) adequada ao ALB

**User Story:** Como responsável pela rede, quero uma VPC com múltiplas AZs, para atender ao requisito do ALB.

#### Critérios de Aceitação
1. O sistema DEVE ter uma VPC com Internet Gateway e route table pública.
2. O sistema DEVE ter pelo menos **duas subnets em AZs diferentes** para o ALB.
3. A documentação DEVE descrever a arquitetura recomendada em produção (EC2 em subnet privada + NAT).

### Requisito 3 — Segurança de rede (Security Groups + SSM)

**User Story:** Como responsável pela segurança, quero expor a EC2 apenas ao ALB, para reduzir a superfície de ataque.

#### Critérios de Aceitação
1. O SG do ALB DEVE permitir entrada nas portas **80 e 443**.
2. O SG da EC2 DEVE permitir HTTP (80) **somente a partir do SG do ALB**.
3. O sistema NÃO DEVE liberar a porta HTTP da EC2 diretamente para a Internet.
4. A administração da EC2 DEVE ser feita via **SSM Session Manager** (sem SSH/porta 22).

### Requisito 4 — Aplicação (EC2 + Nginx + Health Check)

**User Story:** Como estudante, quero uma aplicação simples com health check, para o Target Group considerar a instância saudável.

#### Critérios de Aceitação
1. A EC2 DEVE rodar Ubuntu Linux com Nginx habilitado e iniciado.
2. O Nginx DEVE servir `index.html` e um endpoint `/health`.
3. O endpoint `/health` DEVE responder **HTTP 200** com corpo `{"status":"healthy"}`.
4. O Target Group DEVE usar Health Check Path `/health` e código de sucesso `200`.
5. A aplicação NÃO DEVE conter nenhum endpoint vulnerável nem ler arquivos do sistema.

### Requisito 5 — HTTPS e domínio próprio

#### Critérios de Aceitação
1. O sistema DEVE usar um certificado ACM na **mesma região do ALB**, validado por DNS.
2. Os listeners do ALB DEVEM ter **80 → Redirect → 443 (HTTPS)**.
3. O Route 53 DEVE ter registros Alias apontando cada subdomínio para seu ALB.

### Requisito 6 — Regra de WAF para Path Traversal

#### Critérios de Aceitação
1. O sistema DEVE ter uma Web ACL **regional** chamada `waf-lab-path-traversal`.
2. A Web ACL DEVE conter uma única regra `Block-Path-Traversal-Lab`.
3. A regra DEVE detectar `../` (e a forma `%2e%2e%2f`) na query string (e opcionalmente no URI path), com transformação **URL decode**.
4. A ação DEVE ser **Block** e a ação padrão DEVE ser **Allow**.
5. A Web ACL DEVE ser associada **somente** ao ALB com WAF.
6. O sistema NÃO DEVE usar Bot Control, Fraud Control, Marketplace Rules ou Managed Rule Groups desnecessários.

### Requisito 7 — Comportamento comprovável (access.log)

#### Critérios de Aceitação
1. QUANDO uma requisição normal é enviada a qualquer endpoint ENTÃO ela DEVE chegar ao Nginx.
2. QUANDO uma requisição de Path Traversal é enviada ao endpoint sem WAF ENTÃO ela DEVE chegar ao Nginx e **aparecer no `access.log`**.
3. QUANDO uma requisição de Path Traversal é enviada ao endpoint com WAF ENTÃO o sistema DEVE responder **403** e a requisição **não** DEVE aparecer no `access.log`.
4. O bloqueio DEVE ser visível no CloudWatch (WAF: `BlockedRequests`; ALB: `HTTPCode_ELB_4XX_Count`, `HealthyHostCount`).

### Requisito 8 — Scripts de teste controlado

#### Critérios de Aceitação
1. O sistema DEVE fornecer `test-path-traversal.py` e `test-path-traversal.ps1`.
2. Os scripts DEVEM receber as URLs sem WAF e com WAF.
3. Os scripts DEVEM executar apenas uma requisição normal e uma de Path Traversal por endpoint (sem threads, flood ou DDoS).
4. Os scripts DEVEM tratar **403** como "bloqueado" e outros códigos como "chegou ao servidor".

### Requisito 9 — Segurança, custo e exclusão

#### Critérios de Aceitação
1. Os testes DEVEM ser executados somente contra a própria infraestrutura do laboratório.
2. O laboratório NÃO DEVE explorar arquivos reais, criar shell, execução remota, DDoS ou stress.
3. O laboratório DEVE usar 1 Web ACL + 1 regra + poucas requisições.
4. A documentação DEVE alertar que ALB e EC2 cobram por hora e fornecer procedimento de exclusão.
