# Design — Lab 03: Proteção contra SQL Injection (API Gateway REST + Lambda)

## Visão geral

Uma única REST API com integração Lambda é exposta por dois stages e dois Custom Domains. Apenas o stage `com-waf` tem uma Web ACL regional associada. A única variável entre os caminhos é o WAF. Não há banco de dados.

```
                             INTERNET
                                |
                             Route 53
                 +--------------+--------------+
                 v                             v
      api-sem-waf.dev.inhesta.net   api-com-waf.dev.inhesta.net
                 v                             v
          API Gateway (stage sem-waf)   API Gateway (stage com-waf)
                 |                             |
                 |                        AWS WAF (regional)
                 +--------------+--------------+
                                v
                             Lambda
                                v
                              JSON
```

## Componentes e decisões

| Componente | Decisão | Motivo |
|---|---|---|
| Lambda | Uma função, rotas /health, /produto, /search, /info; sem banco | Foco em testar o WAF, não SQL real |
| API Gateway | REST API Regional, integração proxy, 2 stages | Mesmo código com/sem WAF |
| Custom Domains | `api-sem-waf`→stage sem-waf; `api-com-waf`→stage com-waf | URLs limpas por stage |
| ACM | Certificado na região da API, validação DNS | Custom Domain Regional |
| AWS WAF | Web ACL regional, 1 regra SQLi, Block, só no stage com-waf | Escopo regional; custo mínimo |
| CloudWatch | Logs/métricas do WAF, API GW e Lambda | Comprovar que a Lambda não executa |

## Fluxo sem WAF

`Usuário → Route 53 → API Gateway (stage sem-waf) → Lambda`. A requisição de SQLi chega à Lambda, que ecoa o parâmetro (200) e registra o log.

## Fluxo com WAF

`Usuário → Route 53 → API Gateway (stage com-waf) → AWS WAF → (detecta SQLi) → BLOCK → 403`. A Lambda **não** é invocada.

## Regra `Block-SQLi-Lab`

- **Statement:** SQLi match (SQL injection attack).
- **Componente inspecionado:** Todos os parâmetros de consulta.
- **Transformação de texto:** URL decode (opcional: HTML entity decode).
- **Ação:** Block. Ação padrão da Web ACL: Allow.

Payload de teste: `?id=1' OR '1'='1`. A Lambda apenas ecoa o parâmetro; não há banco nem execução de SQL.

## Evidência central: Lambda não executa

O ponto-chave é comparar CloudWatch Logs (`/aws/lambda/lambda-waf-lab03`) e a métrica `Invocations`: no stage sem WAF a chamada de SQLi gera log e incrementa Invocations; no stage com WAF não há log nem incremento (bloqueio no WAF antes da integração).

## Artefatos do projeto

- Lambda: `aws-waf-lab-03-sqli/lambda/lambda_function.py`.
- Testes: `aws-waf-lab-03-sqli/tests/` (`test-sqli.py`, `.ps1`).
- Documentação de apoio: `README.md`, `ARQUITETURA.md`, `IMPLANTACAO.md`, `TESTE.md`.

## Estratégia de teste

1. **Validação local (Kiro):** sintaxe do `lambda_function.py` e dos scripts de teste; opcionalmente simular um evento de API Gateway e conferir a resposta JSON.
2. **Validação na AWS (manual):** rodar scripts (sem WAF SQLi → 200; com WAF SQLi → 403); confirmar ausência de log/Invocations no stage com WAF; conferir CloudWatch.

## Referências de nomes (ambiente real)

| Item | Valor |
|---|---|
| Lambda | `lambda-waf-lab03` |
| REST API | `api-waf-lab03` |
| Stages | `sem-waf` / `com-waf` |
| Subdomínios | `api-sem-waf.dev.inhesta.net` / `api-com-waf.dev.inhesta.net` |
| Web ACL / Regra | `waf-lab-sqli` / `Block-SQLi-Lab` |
