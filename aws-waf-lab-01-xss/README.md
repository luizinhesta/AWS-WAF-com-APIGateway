# AWS WAF Security Lab — Projeto 01

## Proteção contra XSS com CloudFront e Amazon S3

Laboratório educacional que demonstra, de forma prática e controlada, a diferença entre uma aplicação **SEM AWS WAF** e uma aplicação **COM AWS WAF**, usando **Cross-Site Scripting (XSS)** como teste principal.

> Primeiro projeto de uma série de laboratórios sobre AWS WAF.

---

## Objetivo

Publicar **dois endpoints** que servem exatamente o **mesmo conteúdo** de um único bucket S3 privado:

- **SEM WAF** — uma requisição com padrão de XSS chega normalmente à origem.
- **COM WAF** — a mesma requisição é **bloqueada com HTTP 403** antes de chegar ao S3.

O endpoint COM WAF tem **duas proteções**:

1. **XSS** (`Block-XSS-Lab`) — bloqueia o padrão de XSS na query string.
2. **Geo-bloqueio** (`Block-Fora-do-Brasil`) — bloqueia **qualquer** requisição de fora do Brasil e responde com uma **página HTML de acesso negado** personalizada (`site/acesso-negado.html`). Para demonstrar, acesse o COM WAF por uma **VPN** ou **instância em outro país**.

O teste de XSS é executado **exclusivamente contra os seus próprios endpoints** de laboratório. É um teste defensivo: mostra o WAF **bloqueando** um padrão de ataque, sem explorar nenhuma vítima.

### O que este laboratório NÃO faz

- Não cria DDoS.
- Não faz stress test.
- Não executa ataques contra sistemas externos.
- Não gera grande volume de requisições (os testes fazem 4 requisições no total).
- Não usa Bot Control, Fraud Control, CAPTCHA pago, Marketplace Rules ou pacotes premium.

---

## O que é XSS (contexto do teste)

**Cross-Site Scripting (XSS)** é uma vulnerabilidade na qual conteúdo contendo scripts maliciosos pode ser enviado para uma aplicação web.

Neste laboratório **nenhum script é efetivamente executado** — o S3 apenas serve arquivos estáticos. O objetivo é enviar uma **string com padrão característico de XSS** na query string e verificar se o AWS WAF identifica e bloqueia a requisição.

Payload usado no teste:

```
?search=<script>alert(1)</script>
```

---

## Serviços AWS utilizados

| Serviço | Papel no laboratório |
|---|---|
| Amazon Route 53 | DNS dos subdomínios do laboratório |
| AWS Certificate Manager (ACM) | Certificado TLS em `us-east-1` para o CloudFront |
| Amazon CloudFront | Duas distribuições (uma sem WAF, uma com WAF) |
| AWS WAF | 1 Web ACL (`waf-lab-xss`) + 2 regras: XSS (`Block-XSS-Lab`) e geo-bloqueio (`Block-Fora-do-Brasil`) com resposta HTML personalizada |
| Amazon S3 | Bucket privado de origem (a mesma origem para as duas distribuições) |
| Amazon CloudWatch | Métricas e requisições amostradas do WAF |

---

## Estrutura do projeto

```
aws-waf-lab-01-xss/
├── site/
│   ├── index.html          (site do laboratório)
│   ├── style.css
│   ├── script.js           (gera as URLs de teste com URL encoding)
│   └── acesso-negado.html  (página HTML de acesso negado — resposta do WAF fora do Brasil)
│
├── tests/
│   ├── test-xss.py     (teste controlado em Python)
│   └── test-xss.ps1    (teste controlado em PowerShell)
│
├── README.md           (este arquivo — explicação do projeto)
├── ARQUITETURA.md      (arquitetura e como ela funciona)
├── IMPLANTACAO.md      (passo a passo completo pelo Console AWS)
└── TESTE.md            (passo a passo de como testar o WAF)
```

---

## Como usar

1. Leia a **arquitetura** em [ARQUITETURA.md](ARQUITETURA.md) para entender o fluxo.
2. Siga o **passo a passo pelo Console** em [IMPLANTACAO.md](IMPLANTACAO.md) — inclui criação de todos os recursos e a exclusão ao final.
3. Teste o WAF seguindo o **passo a passo de teste** em [TESTE.md](TESTE.md) (navegador, scripts e confirmação no CloudWatch).

### Scripts de teste

Python:

```bash
python tests/test-xss.py --sem-waf https://site-sem-waf.SEU-DOMINIO.com --com-waf https://site-com-waf.SEU-DOMINIO.com
```

PowerShell:

```powershell
.\tests\test-xss.ps1 -UrlSemWaf "https://site-sem-waf.SEU-DOMINIO.com" -UrlComWaf "https://site-com-waf.SEU-DOMINIO.com"
```

Saída esperada:

```
========================================
AWS WAF LAB 01 - XSS
========================================

SEM WAF
  Normal.................... 200
  XSS....................... 200

COM WAF
  Normal.................... 200
  XSS....................... 403 BLOCKED

========================================
```

---

## Resultado esperado

| Teste | SEM WAF | COM WAF |
|---|---|---|
| Requisição normal (do Brasil) | 200 | 200 |
| XSS controlado (do Brasil) | 200 | 403 BLOCKED |
| Qualquer rota (de fora do Brasil) | 200 | 403 + página "Acesso negado" |

> Os códigos podem variar conforme a configuração final, mas o objetivo é demonstrar que o endpoint protegido pelo WAF bloqueia o padrão XSS e nega acesso de fora do Brasil.

---

## Custos (leia antes de começar)

O **AWS WAF não possui gratuidade permanente**. Ele cobra por Web ACL, por regra e por milhão de requisições avaliadas, enquanto existir. Este laboratório usa o mínimo de recursos (1 Web ACL + 2 regras: XSS e geo-bloqueio + poucas requisições) e evita recursos premium.

- ACM é gratuito para uso em CloudFront.
- CloudFront e S3 têm uso mínimo neste lab.
- Route 53 cobra pela zona hospedada (que você provavelmente já possui).
- **A Web ACL do WAF é o principal custo contínuo — exclua-a ao terminar.**

A seção final de [IMPLANTACAO.md](IMPLANTACAO.md) traz o passo a passo de **exclusão de todos os recursos**.

---

## Uso responsável

Execute os testes **somente** contra os dois endpoints deste laboratório (`site-sem-waf.SEU-DOMINIO.com` e `site-com-waf.SEU-DOMINIO.com`). Não execute ataques contra terceiros e não gere flood, stress test ou DDoS.
