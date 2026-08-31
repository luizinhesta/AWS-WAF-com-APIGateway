# Implantação — Passo a Passo pelo Console AWS

Guia completo de implantação do laboratório **exclusivamente pelo Console AWS**, em português.

> Substitua `SEU-DOMINIO.com` pelo seu domínio real e escolha uma **região** para o laboratório (ex.: `us-east-1` ou `sa-east-1`). O **WAF regional**, o **ACM** e o **Custom Domain Regional** devem ficar na **mesma região** da API.

> **A sequência importa.** Ordem: **Lambda → REST API + rotas → Deploy dos 2 stages → ACM → Custom Domains → Mapeamentos → Route 53 → WAF (só no stage com-waf) → Testes → Exclusão**.

---

## Antes de começar

- Conta AWS com permissões para Lambda, API Gateway, WAF, ACM, Route 53, IAM e CloudWatch.
- Domínio com **zona hospedada no Route 53** (ex.: `SEU-DOMINIO.com`).
- Escolha a **região** e mantenha-a selecionada durante todo o lab.

Nomes de referência:

| Item | Valor sugerido |
|---|---|
| Função Lambda | `lambda-waf-lab03` |
| REST API | `api-waf-lab03` |
| Stage sem WAF | `sem-waf` |
| Stage com WAF | `com-waf` |
| Subdomínio sem WAF | `api-sem-waf.SEU-DOMINIO.com` |
| Subdomínio com WAF | `api-com-waf.SEU-DOMINIO.com` |
| Web ACL | `waf-lab-sqli` |
| Regra do WAF | `Block-SQLi-Lab` |

---

## Etapa 1 — Função Lambda

1. Abra o serviço **Lambda > Criar função**.
2. Selecione **Criar do zero (Author from scratch)**.
3. **Nome da função:** `lambda-waf-lab03`.
4. **Runtime:** **Python 3.12** (ou a versão Python mais recente disponível).
5. **Arquitetura:** padrão (`x86_64`).
6. Clique em **Criar função**.
7. Na aba **Código**, substitua o conteúdo de `lambda_function.py` pelo conteúdo do arquivo `lambda/lambda_function.py` deste projeto.
8. Clique em **Deploy (Implantar)**.

> A função não precisa de permissões extras (não acessa banco nem outros serviços). O CloudWatch Logs é criado automaticamente pela role de execução padrão da Lambda.

---

## Etapa 2 — REST API e rotas

1. Abra **API Gateway > Criar API**.
2. Em **REST API**, clique em **Criar** (não escolha "REST API Privada" nem "HTTP API").
3. **Nome da API:** `api-waf-lab03`. **Tipo de endpoint:** **Regional**.
4. Clique em **Criar API**.

### 2.1 Criar os recursos e métodos

Para cada rota (`/health`, `/produto`, `/search`, `/info`), o caminho mais simples é usar **integração proxy**:

Opção recomendada (proxy `{proxy+}`), que encaminha todas as rotas para a Lambda:

1. Selecione o recurso raiz **/** e em **Ações > Criar recurso**.
2. Marque **Recurso proxy (Proxy resource)**; o nome vira `{proxy+}`.
3. Marque **Habilitar integração de proxy do Lambda**.
4. Clique em **Criar recurso**; selecione a Lambda `lambda-waf-lab03` e confirme as permissões.
5. Também crie um método **ANY** no recurso raiz **/** com integração proxy para a mesma Lambda (para atender `GET /` e `GET /health` na raiz).

> Alternativa explícita: criar os recursos `/health`, `/produto`, `/search`, `/info` e, em cada um, um método **GET** com **Integração de proxy do Lambda** apontando para `lambda-waf-lab03`.

### 2.2 Implantar (deploy) nos dois stages

1. **Ações > Implantar API**.
2. Em **Estágio de implantação**, selecione **[Novo estágio]** e nomeie **`sem-waf`**. Clique em **Implantar**.
3. Repita **Ações > Implantar API** criando o estágio **`com-waf`**.
4. Anote as **Invoke URLs** dos dois stages (algo como `https://xxxx.execute-api.REGIAO.amazonaws.com/sem-waf`).

Teste rápido pelas Invoke URLs:
```
https://xxxx.execute-api.REGIAO.amazonaws.com/sem-waf/health
```
Deve retornar o JSON de health.

---

## Etapa 3 — Certificado ACM (regional)

> Para Custom Domain **Regional**, o certificado deve estar na **mesma região** da API.

1. Confirme a **região** do laboratório.
2. Abra **ACM > Solicitar > Solicitar um certificado público**.
3. Domínios:
   - `api-sem-waf.SEU-DOMINIO.com`
   - Adicione `api-com-waf.SEU-DOMINIO.com` (ou use `*.SEU-DOMINIO.com`).
4. **Validação por DNS**. Clique em **Solicitar**.
5. Abra o certificado e clique em **Criar registros no Route 53**.
6. Aguarde o status **Emitido**.

---

## Etapa 4 — Custom Domains do API Gateway

Crie **dois** domínios personalizados.

### 4.1 api-sem-waf

1. Abra **API Gateway > Nomes de domínio personalizados > Criar**.
2. **Nome de domínio:** `api-sem-waf.SEU-DOMINIO.com`.
3. **Tipo de endpoint:** **Regional**.
4. **Certificado ACM:** selecione o certificado da Etapa 3.
5. Clique em **Criar nome de domínio**.
6. Abra o domínio criado, vá em **Mapeamentos de API (API mappings) > Configurar mapeamentos**:
   - **API:** `api-waf-lab03`.
   - **Estágio:** `sem-waf`.
   - (Caminho vazio para mapear na raiz.)
   - **Salvar**.
7. Anote o **domínio de destino do API Gateway** (algo como `dxxxx.execute-api...` ou um alvo regional) — será usado no Route 53.

### 4.2 api-com-waf

1. Repita criando `api-com-waf.SEU-DOMINIO.com` (Regional, mesmo certificado).
2. Em **Mapeamentos de API**, mapeie para a API `api-waf-lab03`, **estágio `com-waf`**.
3. Anote o domínio de destino.

---

## Etapa 5 — Route 53 (registros Alias)

1. Abra **Route 53 > Zonas hospedadas > `SEU-DOMINIO.com`**.
2. **Criar registro:**
   - **Nome:** `api-sem-waf`. **Tipo:** **A**. Ative **Alias**.
   - **Rotear tráfego para:** **Alias para API Gateway** → região do lab → selecione o alvo do Custom Domain `api-sem-waf`.
   - **Criar registros**.
3. Repita para `api-com-waf` apontando para o Custom Domain `api-com-waf`.
4. Aguarde a propagação DNS.

---

## Etapa 6 — AWS WAF (pacote de proteção `waf-lab-sqli` + regra SQLi)

> A Web ACL deve ser **regional** e criada na **mesma região** da API. Ela será associada **somente ao stage `com-waf`**.

1. Na busca do Console, digite **WAF** e abra **AWS WAF & Shield**.
2. No menu à esquerda, clique em **Web ACLs**.
3. No seletor **Escopo da região** (topo da lista), selecione **Regional** e confirme a **região da API**.
4. Clique em **Criar pacote de proteção (ACL da Web)**.

**Conte-nos sobre sua aplicação**

1. Em **Categoria da aplicação** (obrigatório), abra o dropdown e escolha uma categoria genérica (ex.: **Outro**).
2. Em **Foco da aplicação**, selecione **API** (o lab expõe uma API Gateway REST consumida programaticamente).

**Selecione recursos para proteger**

1. Clique em **Adicionar recursos** e escolha **Adicionar recursos regionais**.
2. Na lista, selecione o tipo **API Gateway**, escolha a API `api-waf-lab03` e marque o **stage `com-waf`** (**somente** ele — não marque o `sem-waf`). Clique em **Adicionar**.
   - Se preferir, clique em **Ignorar por enquanto** e associe depois (ver nota no fim da etapa).

**Escolher proteções iniciais**

1. **Não selecione nenhum pacote gerenciado (Managed Rule Group).** Deixe vazio — usaremos apenas 1 regra customizada de SQLi.

**Nome e descrição**

1. Em **Nome**, digite `waf-lab-sqli`.
2. Em **Descrição** (opcional), digite `Lab 03 - bloqueio de SQL Injection`.
3. Deixe **Métricas do CloudWatch** e **Solicitações de amostra** habilitadas.

**Personalizar pacote de proteção — adicionar a regra SQLi**

1. Expanda **Personalizar pacote de proteção (ACL da Web)**.
2. Clique em **Adicionar regras > Adicionar minha própria regra e grupos de regras** e escolha **Construtor de regras (Rule builder)**.
3. Em **Nome**, digite `Block-SQLi-Lab`. Em **Tipo**, deixe **Regra normal**.
4. Em **Instrução (Statement)**:
    - **Inspecionar:** selecione **Todos os parâmetros de consulta (All query parameters)** — ou **Query string**.
    - **Tipo de correspondência:** selecione **Ataque de injeção de SQL (SQL injection attack)**.
    - **Transformação de texto:** clique em **Adicionar** e escolha **URL decode** (opcional: também **HTML entity decode**).
5. Em **Ação (Action)**, selecione **Bloquear (Block)**.
6. Clique em **Adicionar regra**.
7. Em **Ação padrão da Web ACL**, deixe **Permitir (Allow)**.
8. Revise e clique em **Criar pacote de proteção (ACL da Web)**.

> Para associar o stage depois (se você pulou o passo 7-8): **WAF > Web ACLs > `waf-lab-sqli` > aba Recursos AWS associados > Adicionar recursos AWS**, escolha API Gateway e selecione o stage `com-waf`.

> **Importante:** associe a Web ACL **apenas** ao stage `com-waf`. O stage `sem-waf` fica sem WAF.

> Se preferir associar depois: **WAF > Web ACLs > `waf-lab-sqli` > Recursos AWS associados > Adicionar recursos AWS**, escolha API Gateway e selecione o stage `com-waf`.

---

## Etapa 7 — Testes

Veja o passo a passo completo em [TESTE.md](TESTE.md). Resumo:

- **SEM WAF:** `/health` 200, `/produto?id=123` 200, `/produto?id=1' OR '1'='1` 200 (Lambda executa).
- **COM WAF:** `/health` 200, `/produto?id=123` 200, `/produto?id=1' OR '1'='1` **403** (Lambda **não** executa).

Scripts:

```bash
python tests/test-sqli.py --sem-waf https://api-sem-waf.SEU-DOMINIO.com --com-waf https://api-com-waf.SEU-DOMINIO.com
```

```powershell
.\tests\test-sqli.ps1 -ApiSemWaf "https://api-sem-waf.SEU-DOMINIO.com" -ApiComWaf "https://api-com-waf.SEU-DOMINIO.com"
```

---

## Etapa 8 — Exclusão de recursos (faça ao terminar)

> A **Web ACL do WAF é o principal custo contínuo**. Exclua tudo ao concluir. Ordem inversa da criação.

### 8.1 Route 53
- Exclua os registros `api-sem-waf` e `api-com-waf`.

### 8.2 AWS WAF
1. **WAF > Web ACLs > `waf-lab-sqli`**.
2. Em **Recursos AWS associados**, remova a associação com o stage `com-waf`.
3. Exclua a Web ACL.

### 8.3 Custom Domains
- **API Gateway > Nomes de domínio personalizados**, exclua `api-sem-waf...` e `api-com-waf...`.

### 8.4 REST API
- **API Gateway > APIs**, exclua a API `api-waf-lab03`.

### 8.5 Lambda
- **Lambda > Funções**, exclua `lambda-waf-lab03`.

### 8.6 CloudWatch Logs (opcional)
- **CloudWatch > Log groups**, exclua `/aws/lambda/lambda-waf-lab03` e os logs de acesso da API, se criados.

### 8.7 ACM (opcional)
- Exclua o certificado se não for reutilizar (só é possível quando não estiver associado a nenhum Custom Domain).

### Checklist final
- [ ] Registros Alias removidos do Route 53
- [ ] Web ACL `waf-lab-sqli` desassociada e excluída
- [ ] Dois Custom Domains excluídos
- [ ] REST API excluída
- [ ] Função Lambda excluída
- [ ] Log groups removidos (opcional)
- [ ] Certificado ACM excluído (opcional)
- [ ] Nenhum recurso do laboratório restante gerando custo

---

## Solução de problemas rápida

| Sintoma | O que verificar |
|---|---|
| COM WAF **não** bloqueia o SQLi (200) | Web ACL associada ao stage `com-waf`? Regra com ação **Block**? Inspecionando query string? Transformação **URL decode**? |
| SEM WAF retorna 403 | O stage `sem-waf` não deve ter Web ACL associada. |
| 403 em **todas** as rotas COM WAF | A regra SQLi não deveria bloquear `/health` nem `/produto?id=123` — revise a instrução da regra. |
| Custom Domain não resolve | Registro Alias correto no Route 53 apontando para o alvo do Custom Domain; aguarde propagação. |
| Certificado não aparece no Custom Domain | Precisa estar **Emitido** e na **mesma região** (Custom Domain Regional). |
| `{proxy+}` retorna 403/Missing Authentication | Verifique o mapeamento de API e se o método/integração proxy foi criado e implantado nos stages. |
| Lambda não responde | Confirme o **Deploy** do código e a permissão de invocação concedida ao API Gateway. |
