# Design — Lab 01: Proteção contra XSS (CloudFront + S3)

## Visão geral

O laboratório expõe dois subdomínios que servem o mesmo site estático de um único bucket S3 privado. Cada subdomínio tem sua própria distribuição CloudFront. Apenas a distribuição "com WAF" está associada a uma Web ACL com uma regra de XSS. A única variável entre os dois caminhos é o WAF.

```
                          INTERNET
                             |
                          Route 53
                             |
             +---------------+---------------+
             |                               |
             v                               v
   site-sem-waf.dev.inhesta.net    site-com-waf.dev.inhesta.net
             |                               |
             v                               v
   CloudFront (sem WAF)             CloudFront (com WAF)
             |                               |
             |                            AWS WAF (waf-lab-xss)
             |                               |
             +---------------+---------------+
                             |
                             v
                        S3 privado (OAC)
                             |
                        index.html
```

## Componentes e decisões

| Componente | Decisão de design | Motivo |
|---|---|---|
| Amazon S3 | Bucket privado, Block Public Access, acesso só via OAC | Origem única e segura; isola o WAF como única variável |
| ACM | Certificado em `us-east-1`, validação DNS | CloudFront só aceita certificado em us-east-1 |
| CloudFront | Duas distribuições, Redirect HTTP→HTTPS, Default root object `index.html` | Compara com/sem WAF servindo o mesmo conteúdo |
| AWS WAF | Web ACL escopo CloudFront (global), 1 regra XSS, ação Block | Escopo exigido para CloudFront; 1 regra = custo mínimo |
| Route 53 | Registros Alias A para cada distribuição | DNS para os subdomínios |
| CloudWatch | Métricas + Sampled Requests habilitados | Comprovar o bloqueio |

## Fluxo sem WAF

`Usuário → Route 53 → CloudFront (sem Web ACL) → S3`. A requisição com XSS não é inspecionada e chega à origem (tende a 200).

## Fluxo com WAF

`Usuário → Route 53 → CloudFront → AWS WAF → (detecta XSS) → BLOCK → 403`. A requisição com XSS é bloqueada antes de chegar ao S3.

## Regra `Block-XSS-Lab`

- **Statement:** XSS match (Cross-site scripting).
- **Componente inspecionado:** Todos os parâmetros de consulta (query string).
- **Transformação de texto:** URL decode (opcional: HTML entity decode).
- **Ação:** Block.
- **Ação padrão da Web ACL:** Allow.

Payload de teste: `?search=<script>alert(1)</script>`. Nenhum script é executado — o S3 serve arquivos estáticos; a string existe apenas para o WAF inspecionar.

## Acesso privado ao S3 (OAC)

- Bucket privado com Block Public Access.
- CloudFront assina as requisições à origem via OAC (criado automaticamente ao marcar "Allow private S3 bucket access to CloudFront" no assistente).
- Bucket policy autoriza `cloudfront.amazonaws.com` restrito às duas distribuições via `AWS:SourceArn`.
- Como as duas distribuições usam o mesmo bucket, a policy final precisa listar **ambas** as distribuições.

## Artefatos do projeto

- Site: `aws-waf-lab-01-xss/site/` (`index.html`, `style.css`, `script.js`).
- Testes: `aws-waf-lab-01-xss/tests/` (`test-xss.py`, `test-xss.ps1`).
- Documentação de apoio: `README.md`, `ARQUITETURA.md`, `IMPLANTACAO.md`, `TESTE.md`.

## Estratégia de teste

1. **Validação local (Kiro):** conferir que os scripts Python rodam sem erro de sintaxe, que o HTML abre no navegador e que a lógica de montagem de URL/encoding está correta.
2. **Validação na AWS (manual):** após implantar, rodar os scripts contra os dois endpoints e confirmar 200 (sem WAF, XSS) vs 403 (com WAF, XSS), além de conferir CloudWatch/Sampled Requests.

## Referências de nomes (ambiente real)

| Item | Valor |
|---|---|
| Bucket S3 | `waf-lab-01-xss-SUFIXO` |
| Distribuição sem WAF | `waf-lab-01-xss-sem-waf` |
| Distribuição com WAF | `waf-lab-01-xss-com-waf` |
| Subdomínio sem WAF | `site-sem-waf.dev.inhesta.net` |
| Subdomínio com WAF | `site-com-waf.dev.inhesta.net` |
| Web ACL | `waf-lab-xss` |
| Regra | `Block-XSS-Lab` |
| Certificado ACM | `*.dev.inhesta.net` (us-east-1) |
