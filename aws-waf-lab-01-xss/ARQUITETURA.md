# Arquitetura

Este documento descreve a arquitetura do laboratório e **como ela funciona**.

---

## Visão geral

O laboratório expõe **dois subdomínios** que servem o **mesmo conteúdo** de um único bucket S3 privado. A única diferença entre eles é que apenas uma das distribuições CloudFront está associada a uma Web ACL do AWS WAF.

```
                          INTERNET
                             |
                         Route 53
                             |
             +---------------+---------------+
             |                               |
             v                               v
  site-sem-waf.dominio.com        site-com-waf.dominio.com
             |                               |
             v                               v
    CloudFront SEM WAF              CloudFront COM WAF
             |                               |
             |                            AWS WAF
             |                               |
             +---------------+---------------+
                             |
                             v
                        S3 PRIVADO
                             |
                        index.html
```

> **O mesmo bucket S3** é a origem das duas distribuições CloudFront. Isso garante que a única variável entre os endpoints seja a presença (ou não) do WAF.

---

## Componentes

| Componente | Função |
|---|---|
| **Route 53** | Zona hospedada do domínio com 2 registros Alias (tipo A) apontando para as duas distribuições CloudFront. |
| **ACM** | Certificado TLS público em `us-east-1` (obrigatório para CloudFront), validado por DNS. Habilita HTTPS. |
| **CloudFront SEM WAF** | Distribuição com OAC, HTTPS, **sem** Web ACL associada. |
| **CloudFront COM WAF** | Distribuição com OAC, HTTPS, **associada** à Web ACL `waf-lab-xss`. |
| **AWS WAF** | 1 Web ACL de escopo **CloudFront (Global)** com 2 regras: `Block-XSS-Lab` (XSS match statement) e `Block-Fora-do-Brasil` (geo match, com resposta HTML personalizada). |
| **Amazon S3** | Bucket **privado**, com Block Public Access ativado. Acesso somente via OAC do CloudFront. |
| **CloudWatch** | Métricas `AllowedRequests` / `BlockedRequests` e Sampled Requests do WAF. |

---

## Como funciona o fluxo SEM WAF

```
Usuário
  ↓
Route 53  (resolve site-sem-waf.dominio.com para o CloudFront)
  ↓
CloudFront SEM WAF  (sem Web ACL)
  ↓
S3 privado  (via OAC)
```

Como **não há Web ACL** associada, uma requisição com padrão de XSS não é inspecionada pelo WAF e **chega à origem normalmente** (tende a retornar `200`).

---

## Como funciona o fluxo COM WAF

```
Usuário
  ↓
Route 53  (resolve site-com-waf.dominio.com para o CloudFront)
  ↓
CloudFront COM WAF
  ↓
AWS WAF  (Web ACL waf-lab-xss)
  ↓
Block-Fora-do-Brasil  → origem fora do BR? → BLOCK (403 + página "Acesso negado")
  ↓ (origem no Brasil)
Block-XSS-Lab         → padrão de XSS na query string? → BLOCK (403 padrão)
  ↓ (sem XSS)
S3 privado (via OAC)
```

O AWS WAF é avaliado **na borda do CloudFront, antes da origem**. Se a origem estiver fora do Brasil, a regra `Block-Fora-do-Brasil` bloqueia e retorna **HTTP 403** com a **página HTML personalizada** de acesso negado. Se a origem for o Brasil mas a query string contiver o padrão de XSS, a regra `Block-XSS-Lab` bloqueia com **HTTP 403**. Em ambos os casos o S3 **não** é acessado.

---

## Como funciona a regra de XSS

- **Tipo:** XSS match statement (correspondência de cross-site scripting).
- **Componente inspecionado:** a **query string** / todos os argumentos de query.
- **Transformações de texto:** `URL_DECODE` (e opcionalmente `HTML_ENTITY_DECODE`), para o WAF enxergar o payload já decodificado, mesmo com URL encoding.
- **Ação:** `BLOCK`.
- **Ação padrão da Web ACL:** `Allow` (tudo passa, exceto o que a regra bloqueia).

O XSS match statement procura por padrões característicos de scripts (por exemplo `<script>`). Assim, `?search=<script>alert(1)</script>` é identificado e bloqueado, enquanto `?search=teste` passa normalmente.

---

## Como funciona a regra de Geo-bloqueio (fora do Brasil)

- **Regra:** `Block-Fora-do-Brasil`.
- **Tipo:** Geographic match (correspondência geográfica) com **Negate statement** ativo → corresponde quando o país de origem **não** é o Brasil.
- **Configuração:** país = **Brazil (BR)**; IP usado = **Source IP address** (IP de origem da requisição).
- **Ação:** `BLOCK` com **resposta personalizada**: código `403` e corpo HTML `acesso-negado-br` (o conteúdo de `site/acesso-negado.html`).

O WAF determina o país pela **geolocalização do IP de origem**. Requisições do Brasil não correspondem à regra e seguem para a inspeção de XSS; requisições de qualquer outro país recebem **HTTP 403** com a **página de acesso negado** renderizada no navegador.

```
Origem no Brasil        →  regra NÃO corresponde  →  segue para a regra XSS
Origem fora do Brasil   →  regra corresponde       →  BLOCK (403 + página HTML)
```

### Resposta personalizada (custom response)

- O corpo HTML é cadastrado uma vez na Web ACL em **Corpos de resposta personalizados** com o nome `acesso-negado-br` e tipo **HTML** (limite de ~10 KB).
- A regra de geo referencia esse corpo e define o **status 403**.
- A página é **autocontida** (CSS embutido, sem dependências externas), pois o WAF entrega apenas o HTML — não busca arquivos no S3.

---

## Ordem de avaliação das regras

Recomenda-se `Block-Fora-do-Brasil` com **prioridade mais alta** (avaliada primeiro): uma origem estrangeira recebe a página de acesso negado antes de qualquer inspeção de XSS. Efeitos combinados:

- Fora do Brasil → **403 + página de acesso negado** (geo vence).
- Do Brasil **com** XSS → **403** padrão (regra XSS).
- Do Brasil **sem** XSS → passa para o S3.

---

## Como funciona o acesso privado ao S3 (OAC)

- O bucket S3 fica **privado**, com **Block Public Access** ligado — ninguém acessa direto pela internet.
- O CloudFront usa **Origin Access Control (OAC)** para assinar as requisições à origem.
- A **bucket policy** do S3 permite apenas o serviço `cloudfront.amazonaws.com`, restrito às duas distribuições deste laboratório (via `AWS:SourceArn`).

Resultado: o conteúdo só é servido **através do CloudFront**, nunca por acesso direto ao S3.

---

## Decisões de projeto

- **Mesma origem S3** para as duas distribuições: isola o WAF como única variável.
- **Escopo CloudFront (Global)** no WAF: exigido para associar a Web ACL a distribuições CloudFront; é gerenciado a partir de `us-east-1`.
- **OAC** em vez de OAI (legado): é o método atual e recomendado pela AWS para acesso privado ao S3.
- **Certificado ACM em `us-east-1`**: o CloudFront só aceita certificados dessa região.
- **2 regras** (`Block-XSS-Lab` + `Block-Fora-do-Brasil`): uma demonstra inspeção de conteúdo (XSS), a outra controle por origem geográfica com **resposta HTML personalizada**, mantendo o custo baixo.
- **HTTP → Redirect → HTTPS**: configurado na Viewer Protocol Policy do CloudFront.
