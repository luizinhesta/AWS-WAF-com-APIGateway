# AWS WAF Security Lab — Projeto 03

## Proteção contra SQL Injection com API Gateway REST + AWS Lambda

Laboratório educacional que demonstra, de forma prática e controlada, a diferença entre uma aplicação Serverless **SEM AWS WAF** e **COM AWS WAF**, usando **SQL Injection (SQLi)** como teste principal.

> Terceiro projeto da série de laboratórios sobre AWS WAF.

---

## Objetivo

Publicar **dois endpoints** que apontam para a **mesma API** (API Gateway REST + Lambda), diferenciados por **stage**:

- **SEM WAF** (stage `sem-waf`) — uma requisição com padrão de SQL Injection chega à Lambda.
- **COM WAF** (stage `com-waf`) — a mesma requisição é **bloqueada com HTTP 403** antes de chegar à Lambda.

O stage `com-waf` tem **duas proteções**:

1. **SQL Injection** (`Block-SQLi-Lab`) — bloqueia o padrão de SQLi na query string.
2. **Geo-bloqueio** (`Block-Fora-do-Brasil`) — bloqueia **qualquer** requisição cujo IP de origem esteja **fora do Brasil**. Para demonstrar, acesse o `com-waf` a partir de uma **VPN** ou de uma **instância em outro país**: todas as rotas retornam 403.

A principal evidência do laboratório é o **CloudWatch Logs / Invocations da Lambda**: SEM WAF a chamada aparece nos logs (a Lambda executou); COM WAF ela é bloqueada e **não** aparece (a Lambda não executou).

### O que este laboratório NÃO faz

- **Não usa banco de dados** e não executa nenhum comando SQL.
- Não cria banco vulnerável nem vulnerabilidade real.
- Não cria DDoS, stress test ou grande volume de requisições.
- Não usa Bot Control, Fraud Control, Marketplace Rules ou Managed Rule Groups desnecessários.

---

## O que é SQL Injection (contexto do teste)

**SQL Injection** ocorre quando entradas fornecidas pelo usuário são manipuladas para alterar comandos SQL de uma aplicação vulnerável.

Neste laboratório **não existe banco de dados, execução de SQL nem vulnerabilidade real**. Uma string com formato semelhante a SQL Injection é enviada **apenas como parâmetro HTTP** para testar o mecanismo de inspeção do AWS WAF:

```
GET /produto?id=1' OR '1'='1
```

A Lambda apenas **ecoa** o parâmetro `id` de volta. Os scripts de teste aplicam **URL encoding** ao payload automaticamente.

---

## Serviços AWS utilizados

| Serviço | Papel no laboratório |
|---|---|
| Amazon Route 53 | DNS dos subdomínios do laboratório |
| AWS Certificate Manager (ACM) | Certificado TLS regional para os Custom Domains do API Gateway |
| Amazon API Gateway (REST API) | Uma REST API com dois stages (`sem-waf` e `com-waf`) |
| AWS Lambda | Função que responde às rotas (sem banco de dados) |
| AWS WAF | 1 Web ACL **regional** (`waf-lab-sqli`) + 2 regras (`Block-SQLi-Lab` e `Block-Fora-do-Brasil`) |
| Amazon CloudWatch | Métricas e logs do WAF, do API Gateway e da Lambda |

---

## Rotas da API

| Rota | Descrição |
|---|---|
| `GET /health` | Retorna `{"status":"healthy","project":"AWS WAF Security Lab 03"}` |
| `GET /produto?id=123` | Ecoa o parâmetro `id` (sem consultar banco) |
| `GET /search?q=...` | Ecoa o termo de busca |
| `GET /info` (e `GET /`) | Página HTML explicando o laboratório |

---

## Estrutura do projeto

```
aws-waf-lab-03-sqli/
├── lambda/
│   └── lambda_function.py   (função Lambda — rotas /health, /produto, /search, /info)
│
├── tests/
│   ├── test-sqli.py         (teste controlado em Python)
│   └── test-sqli.ps1        (teste controlado em PowerShell)
│
├── README.md                (este arquivo — explicação do projeto)
├── ARQUITETURA.md           (arquitetura, stages e como funciona)
├── IMPLANTACAO.md           (passo a passo completo pelo Console AWS)
└── TESTE.md                 (passo a passo de como testar o WAF)
```

---

## Como usar

1. Leia a **arquitetura** em [ARQUITETURA.md](ARQUITETURA.md).
2. Siga o **passo a passo pelo Console** em [IMPLANTACAO.md](IMPLANTACAO.md) — Lambda, REST API, stages, ACM, Custom Domains, Route 53, WAF e exclusão ao final.
3. Teste o WAF seguindo [TESTE.md](TESTE.md) (scripts, comprovação de que a Lambda não executou e CloudWatch).

### Scripts de teste

Python:

```bash
python tests/test-sqli.py --sem-waf https://api-sem-waf.SEU-DOMINIO.com --com-waf https://api-com-waf.SEU-DOMINIO.com
```

PowerShell:

```powershell
.\tests\test-sqli.ps1 -ApiSemWaf "https://api-sem-waf.SEU-DOMINIO.com" -ApiComWaf "https://api-com-waf.SEU-DOMINIO.com"
```

Saída esperada:

```
=========================================
AWS WAF LAB 03 - SQL INJECTION
=========================================

SEM WAF
  Health..................... 200
  Normal..................... 200
  SQL Injection.............. 200

COM WAF
  Health..................... 200
  Normal..................... 200
  SQL Injection.............. 403 BLOCKED

=========================================
```

---

## Resultado esperado

| Teste | SEM WAF | COM WAF |
|---|---|---|
| Normal (do Brasil) | Lambda executa (200) | Lambda executa (200) |
| SQL Injection (do Brasil) | Lambda executa (200) | WAF bloqueia (403) |
| Qualquer rota (de fora do Brasil) | Lambda executa (200) | WAF bloqueia (403) |

---

## Custos (leia antes de começar)

O **AWS WAF não possui gratuidade permanente**. Este lab usa o mínimo de recursos (1 Web ACL + 2 regras: SQLi e geo-bloqueio + pouquíssimas requisições) e evita recursos premium. API Gateway e Lambda têm free tier generoso e uso mínimo aqui; ACM é gratuito; Route 53 cobra pela zona hospedada. **A Web ACL do WAF é o principal custo contínuo — exclua-a ao terminar.** O passo a passo de exclusão está no final de [IMPLANTACAO.md](IMPLANTACAO.md).

---

## Uso responsável

Execute os testes **somente** contra os seus próprios endpoints (`api-sem-waf.SEU-DOMINIO.com` e `api-com-waf.SEU-DOMINIO.com`). Não ataque serviços externos e não gere flood, stress test ou DDoS.
