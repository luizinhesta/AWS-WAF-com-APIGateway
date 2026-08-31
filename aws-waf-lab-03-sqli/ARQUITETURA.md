# Arquitetura

Este documento descreve a arquitetura do laboratório, o uso de dois stages e **como tudo funciona**.

---

## Visão geral

O laboratório usa **uma única REST API** e **uma única Lambda**, expostas por **dois stages** e **dois Custom Domains**. A única diferença entre os caminhos é que apenas o stage `com-waf` tem uma Web ACL regional associada.

```
                             INTERNET
                                |
                             Route 53
                                |
                +---------------+---------------+
                |                               |
                v                               v
      api-sem-waf.dominio.com         api-com-waf.dominio.com
                |                               |
                v                               v
          API Gateway                       API Gateway
           REST API                          REST API
                |                               |
         Stage sem-waf                    Stage com-waf
                                                |
                                             AWS WAF
                |                               |
                +---------------+---------------+
                                |
                                v
                             Lambda
                                |
                                v
                              JSON
```

> Os dois Custom Domains mapeiam para stages da **mesma** REST API, que integra com a **mesma** Lambda. Assim, a única variável entre os endpoints é a presença do WAF.

---

## Componentes

| Componente | Função |
|---|---|
| **Route 53** | Zona hospedada com 2 registros Alias apontando para os Custom Domains do API Gateway. |
| **ACM** | Certificado TLS regional (mesma região do Custom Domain Regional), validado por DNS. |
| **API Gateway (REST API)** | Uma REST API com integração proxy para a Lambda; dois stages: `sem-waf` e `com-waf`. |
| **Custom Domains** | `api-sem-waf...` → stage `sem-waf`; `api-com-waf...` → stage `com-waf`. |
| **AWS Lambda** | Responde às rotas `/health`, `/produto`, `/search`, `/info`. Não usa banco de dados. |
| **AWS WAF** | Web ACL **regional** `waf-lab-sqli` + regra `Block-SQLi-Lab` (SQLi match statement). |
| **CloudWatch** | Métricas e logs do WAF, do API Gateway e da Lambda. |

---

## Por que dois stages

- Uma REST API pode ter **vários stages** (ex.: `sem-waf` e `com-waf`), cada um com sua própria URL de invocação.
- A Web ACL do WAF é associada **a um stage específico**, não à API inteira. Isso permite ter o **mesmo código** exposto com e sem proteção, isolando o WAF como única variável.
- Cada stage é mapeado a um Custom Domain próprio, para termos URLs limpas (`api-sem-waf...` e `api-com-waf...`).

---

## Como funciona o fluxo SEM WAF

```
Usuário
  ↓
Route 53   (resolve api-sem-waf.dominio.com para o Custom Domain)
  ↓
API Gateway — stage sem-waf   (sem Web ACL)
  ↓
Lambda   (recebe o parâmetro e responde)
```

Como **não há Web ACL** no stage `sem-waf`, a requisição com padrão de SQLi não é inspecionada e **chega à Lambda**, que a processa e responde `200`. A execução aparece no **CloudWatch Logs** da Lambda.

---

## Como funciona o fluxo COM WAF

```
Usuário
  ↓
Route 53   (resolve api-com-waf.dominio.com para o Custom Domain)
  ↓
API Gateway — stage com-waf
  ↓
AWS WAF   (Web ACL waf-lab-sqli)
  ↓
Regra Block-SQLi-Lab detecta o padrão de SQL Injection na query string
  ↓
BLOCK
  ↓
HTTP 403   (a Lambda NÃO é invocada)
```

O AWS WAF é avaliado **no stage do API Gateway, antes da integração com a Lambda**. Quando a regra encontra o padrão de SQLi, retorna **HTTP 403** e a **Lambda não executa** — não há entrada correspondente no CloudWatch Logs nem incremento em `Invocations`. Essa ausência é a principal evidência do laboratório.

---

## Como funciona a regra de SQL Injection

- **Web ACL:** regional (associada a um stage de API Gateway, não ao CloudFront).
- **Regra:** `Block-SQLi-Lab`.
- **Statement:** SQLi match statement (correspondência de SQL Injection).
- **Componente inspecionado:** a **query string** / todos os argumentos de query.
- **Transformações de texto recomendadas:** `URL_DECODE` e `HTML_ENTITY_DECODE` (ajudam o WAF a normalizar o payload). Uma opção adicional é a transformação de sensibilidade específica de SQLi disponível no WAF.
- **Ação:** `BLOCK`.
- **Ação padrão da Web ACL:** `Allow`.

O SQLi match statement procura por padrões característicos de injeção SQL (por exemplo `' OR '1'='1`). Assim, `?id=1' OR '1'='1` é identificado e bloqueado, enquanto `?id=123` passa normalmente.

---

## Comprovação de que a Lambda não executou

Este é o ponto central do laboratório:

- **SEM WAF + SQLi** → a Lambda **executa**: aparece uma linha nos **CloudWatch Logs** (com `method`, `path`, `requestId`) e a métrica `Invocations` incrementa.
- **COM WAF + SQLi** → a Lambda **não executa**: **nenhuma** linha nova nos logs e **nenhum** incremento em `Invocations`. O WAF respondeu 403 antes da integração.

Detalhes de como verificar estão em [TESTE.md](TESTE.md).

---

## Decisões de projeto

- **Mesma API + mesma Lambda, dois stages**: isola o WAF como única variável.
- **Web ACL regional**: exigido para associar a um stage de API Gateway REST (diferente do escopo CloudFront do Lab 01).
- **Sem banco de dados**: o objetivo é testar a inspeção do WAF, não explorar SQL.
- **Logs seguros**: registramos apenas `method`, `path`, `requestId` e o parâmetro recebido — nunca credenciais, tokens ou segredos.
- **1 regra apenas** (`Block-SQLi-Lab`): mantém o custo mínimo e o foco didático.
- **Custom Domains + ACM regional**: URLs limpas e HTTPS, com o certificado na mesma região da API.
