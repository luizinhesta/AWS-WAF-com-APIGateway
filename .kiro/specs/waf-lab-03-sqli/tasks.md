# Tarefas — Lab 03: Proteção contra SQL Injection (API Gateway REST + Lambda)

Implantação **manual pelo Console AWS**. Marque cada item conforme concluir. O detalhamento está em `aws-waf-lab-03-sqli/IMPLANTACAO.md`.

## 1. Lambda
- [ ] 1.1 Criar função `lambda-waf-lab03` (Python 3.12)
- [ ] 1.2 Colar o conteúdo de `lambda/lambda_function.py` e fazer Deploy
- _Requisitos: 2_

## 2. REST API + rotas
- [ ] 2.1 Criar REST API `api-waf-lab03` (endpoint Regional)
- [ ] 2.2 Criar recurso proxy `{proxy+}` + método ANY na raiz, com integração proxy para a Lambda
- _Requisitos: 1, 2_

## 3. Stages
- [ ] 3.1 Implantar (deploy) no stage `sem-waf`
- [ ] 3.2 Implantar (deploy) no stage `com-waf`
- [ ] 3.3 Testar as Invoke URLs (`/health` retorna JSON)
- _Requisitos: 1_

## 4. ACM
- [ ] 4.1 Solicitar certificado público na região da API (subdomínios ou wildcard), validar por DNS
- _Requisitos: 3_

## 5. Custom Domains
- [ ] 5.1 Criar Custom Domain `api-sem-waf` (Regional, cert ACM) e mapear para o stage `sem-waf`
- [ ] 5.2 Criar Custom Domain `api-com-waf` (Regional, cert ACM) e mapear para o stage `com-waf`
- _Requisitos: 1, 3_

## 6. Route 53 (DNS)
- [ ] 6.1 Criar Alias A `api-sem-waf` → Custom Domain sem-waf
- [ ] 6.2 Criar Alias A `api-com-waf` → Custom Domain com-waf
- _Requisitos: 3_

## 7. AWS WAF (pacote de proteção)
- [ ] 7.1 Criar Web ACL `waf-lab-sqli` (Regional, opção "Crie seu próprio pacote")
- [ ] 7.2 Associar o stage `com-waf` da API (Adicionar recursos regionais → API Gateway)
- [ ] 7.3 Adicionar regra `Block-SQLi-Lab`: inspecionar query string, "Contém ataques de injeção de SQL", transformação URL decode, ação Block
- [ ] 7.4 Ação padrão = Allow e criar o pacote
- _Requisitos: 4_

## 8. Testes (validação na AWS)
- [ ] 8.1 Rodar `test-sqli.py` / `.ps1` contra os dois endpoints
- [ ] 8.2 Confirmar: sem WAF SQLi → 200; com WAF SQLi → 403 BLOCKED
- [ ] 8.3 Comprovar que a Lambda NÃO executou no stage com WAF (CloudWatch Logs + métrica Invocations)
- [ ] 8.4 Conferir CloudWatch (WAF `BlockedRequests`; API GW `4XXError`)
- _Requisitos: 5, 6_

## 9. Validação local (Kiro) — opcional
- [ ] 9.1 Verificar sintaxe do `lambda_function.py` e do `test-sqli.py`
- [ ] 9.2 (Opcional) Simular um evento de API Gateway e conferir a resposta JSON
- _Requisitos: 2, 6_

## 10. Encerramento (exclusão de recursos)
- [ ] 10.1 Excluir registros Alias no Route 53
- [ ] 10.2 Desassociar e excluir a Web ACL `waf-lab-sqli`
- [ ] 10.3 Excluir os dois Custom Domains
- [ ] 10.4 Excluir a REST API
- [ ] 10.5 Excluir a função Lambda
- [ ] 10.6 (Opcional) Excluir log groups e certificado ACM
- _Requisitos: 7_
