# Guia de Implantação Manual — AWS WAF Security Lab 03 (SQL Injection)

Este documento descreve o **passo a passo manual** de implantação do laboratório **AWS WAF Security Lab — Projeto 03: Proteção contra SQL Injection com API Gateway REST + AWS Lambda**, realizado inteiramente pelo **Console da AWS em Português (Brasil)**.

> **Escopo:** este é um **guia manual pelo Console** (Requisitos 24.1 e 24.2). O laboratório **não** utiliza infraestrutura como código (Terraform, CloudFormation, CDK, SAM) nem automação de infraestrutura via AWS CLI (Requisito 26.3). Scripts são usados **apenas** para testes da API.

## Convenções deste guia

- Os nomes de menus, abas e botões aparecem em **pt-BR**, com o nome original em inglês entre parênteses quando útil (Requisito 24.2). Exemplo: **Solicitar (Request)**.
- Substitua **`DOMINIO`** pelo seu domínio real, gerenciado em uma zona hospedada (Hosted zone) existente no Route 53 (por exemplo, `exemplo.com.br`).
- Substitua **`REGIAO`** pela região AWS escolhida para os endpoints regionais (por exemplo, `us-east-1` ou `sa-east-1`). **Todos** os recursos regionais (ACM, API Gateway, Custom Domains e Web ACL) devem ficar na **mesma** região (Requisitos 11.3, 14.2).
- Os pontos marcados com **📸 Evidência / Print recomendado** indicam onde capturar telas para comprovação (Requisito 24.6).
- Os blocos **✅ Validação** indicam verificações intermediárias entre as fases (Requisito 24.4).

## Arquitetura-alvo (resumo)

| Componente | Nome / Valor | Observação |
|---|---|---|
| REST API | `api-waf-lab-sqli` | REST API (não HTTP API), endpoint **Regional** |
| Integração | Lambda Proxy | Recurso `{proxy+}` + `ANY` e raiz `/` + `ANY` |
| Função Lambda | Python (`lambda_function.py`) | Trata todas as rotas por roteamento interno |
| Stage sem WAF | `sem-waf` | Sem Web ACL associada |
| Stage com WAF | `com-waf` | Web ACL associada |
| Custom Domain sem WAF | `api-sem-waf.DOMINIO` | Regional → stage `sem-waf` |
| Custom Domain com WAF | `api-com-waf.DOMINIO` | Regional → stage `com-waf` |
| Certificado ACM | `*.DOMINIO` (curinga) | Regional, validação por DNS |
| Web ACL | `waf-lab-sqli` | Escopo REGIONAL, ação padrão ALLOW |
| Regra prioridade 1 | `Block-Fora-do-Brasil` | Geo match (BR com NOT, Source IP), BLOCK |
| Regra prioridade 2 | `Block-SQLi-Lab` | SQL injection match statement, BLOCK |

## Índice das fases

1. Pré-requisitos e escolha da região
2. Solicitar o certificado ACM curinga (`*.DOMINIO`)
3. Validar o certificado por DNS e confirmar a emissão
4. Criar a função Lambda (Python)
5. Publicar o código `lambda_function.py`
6. Criar a REST API `api-waf-lab-sqli`
7. Criar os recursos `{proxy+}` e a raiz `/` com método `ANY` (Lambda Proxy)
8. Implantar (deploy) no stage `sem-waf`
9. Implantar (deploy) no stage `com-waf`
10. Criar o Custom Domain `api-sem-waf.DOMINIO`
11. Criar o Custom Domain `api-com-waf.DOMINIO`
12. Mapear os Custom Domains aos stages
13. Criar os registros Alias no Route 53
14. Criar a Web ACL `waf-lab-sqli` com as regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab`
15. (Referência) Regras e prioridade
16. Confirmar a associação ao stage `com-waf`
17. Testes de validação (comprovação sem WAF x com WAF)
18. Exclusão completa dos recursos (limpeza / teardown)

---

## Fase 1 — Pré-requisitos e escolha da região

**Objetivo:** garantir os pré-requisitos e fixar a região regional do laboratório.

1. Faça login no **Console da AWS**.
2. Confirme que você possui uma **zona hospedada (Hosted zone)** existente no **Route 53** para o domínio `DOMINIO` (Requisito 13). No menu de serviços, abra **Route 53 → Zonas hospedadas (Hosted zones)** e verifique se `DOMINIO` está listado.
3. Escolha a **região** (`REGIAO`) onde ficarão os endpoints regionais. Use o **seletor de região** no canto superior direito do Console e mantenha essa mesma região em **todas** as fases de ACM, API Gateway e WAF (Requisitos 11.3, 14.2).

> ⚠️ **Importante:** o certificado ACM, a REST API, os Custom Domains e a Web ACL **precisam** estar na **mesma região** regional. Não use `us-east-1` só porque é comum em CloudFront — aqui não há CloudFront (endpoints são regionais).

**✅ Validação:**
- A zona hospedada de `DOMINIO` aparece no Route 53.
- A região selecionada no Console é a `REGIAO` que você usará em todo o laboratório.

**📸 Evidência / Print recomendado:** tela da lista de zonas hospedadas do Route 53 mostrando `DOMINIO` e o seletor de região exibindo a `REGIAO`.

---

## Fase 2 — Solicitar o certificado ACM curinga (`*.DOMINIO`)

**Objetivo:** solicitar um certificado TLS que cubra os dois subdomínios do laboratório (Requisitos 11.1, 11.2, 11.4).

1. Confirme que a `REGIAO` está selecionada no seletor de região.
2. Abra **Certificate Manager (ACM)**.
3. Clique em **Solicitar (Request)**.
4. Selecione **Solicitar um certificado público (Request a public certificate)** e avance em **Próximo (Next)**.
5. Em **Nomes de domínio (Fully qualified domain name)**, informe o curinga:
   - `*.DOMINIO`
   - (Opcional, recomendado) Adicione também `DOMINIO` clicando em **Adicionar outro nome a este certificado (Add another name to this certificate)**.

   > O curinga `*.DOMINIO` cobre `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO` com uma única emissão (Requisito 11.2).
6. Em **Método de validação (Validation method)**, selecione **Validação por DNS (DNS validation)** (Requisito 11.4).
7. Em **Algoritmo de chave (Key algorithm)**, mantenha o padrão (RSA 2048).
8. Clique em **Solicitar (Request)**.

**✅ Validação:**
- O certificado aparece na lista do ACM com status **Pendente de validação (Pending validation)**.

**📸 Evidência / Print recomendado:** tela do ACM mostrando o certificado `*.DOMINIO` com status "Pendente de validação".

---

## Fase 3 — Validar o certificado por DNS e confirmar a emissão

**Objetivo:** criar os registros de validação no Route 53 e confirmar a emissão do certificado (Requisito 11.4).

1. No ACM, clique no **ID do certificado** recém-criado para abrir os detalhes.
2. Na seção **Domínios (Domains)**, localize o registro de validação **CNAME** exibido para o domínio.
3. Clique em **Criar registros no Route 53 (Create records in Route 53)** — o ACM oferece essa ação quando o domínio está em uma zona hospedada da mesma conta.
4. Confirme a criação clicando em **Criar registros (Create records)**.

   > Alternativamente, copie o **Nome (Name)** e o **Valor (Value)** do CNAME e crie o registro manualmente em **Route 53 → Zonas hospedadas → DOMINIO → Criar registro (Create record)**.
5. Aguarde a propagação do DNS. O status do certificado mudará de **Pendente de validação (Pending validation)** para **Emitido (Issued)** — normalmente em alguns minutos.

**✅ Validação:**
- O status do certificado é **Emitido (Issued)**.
- O registro CNAME de validação existe na zona hospedada de `DOMINIO`.

> A **associação** deste certificado aos Custom Domains ocorre nas Fases 10 e 11.

**📸 Evidência / Print recomendado:** tela do ACM com o certificado em status "Emitido" e a tela do Route 53 mostrando o registro CNAME de validação.

---

## Fase 4 — Criar a função Lambda (Python)

**Objetivo:** criar a função Lambda que atenderá todas as rotas (Requisito 9.2).

1. Abra **Lambda** (na mesma `REGIAO`).
2. Clique em **Criar função (Create function)**.
3. Selecione **Criar do zero (Author from scratch)**.
4. Preencha:
   - **Nome da função (Function name):** `waf-lab-sqli` (anote o nome; o grupo de logs será `/aws/lambda/waf-lab-sqli`).
   - **Tempo de execução (Runtime):** **Python** (versão suportada mais recente, por exemplo Python 3.12).
   - **Arquitetura (Architecture):** mantenha o padrão (x86_64).
   - **Permissões (Permissions):** mantenha **Criar uma nova função com permissões básicas do Lambda (Create a new role with basic Lambda permissions)** — isso já concede permissão de escrita no CloudWatch Logs.
5. Clique em **Criar função (Create function)**.

**✅ Validação:**
- A função `waf-lab-sqli` aparece criada, com uma função de execução (IAM role) associada com permissões básicas de log.

**📸 Evidência / Print recomendado:** tela de visão geral da função Lambda `waf-lab-sqli` recém-criada.

---

## Fase 5 — Publicar o código `lambda_function.py`

**Objetivo:** enviar o código de roteamento interno da Lambda (Requisitos 7, 9.2).

1. Na função `waf-lab-sqli`, abra a aba **Código (Code)**.
2. No editor, abra o arquivo `lambda_function.py`.
3. Cole o conteúdo do arquivo `lambda/lambda_function.py` deste laboratório (o código que trata `/health`, `/produto`, `/search`, `/`, `/info` e responde 404 para as demais rotas).
4. Confirme que o **Manipulador (Handler)** está definido como `lambda_function.lambda_handler` (aba **Configuração de tempo de execução (Runtime settings)**).
5. Clique em **Implantar (Deploy)** para salvar e publicar o código.
6. (Recomendado) Ajuste o **Tempo limite (Timeout)** para pelo menos **10 segundos** em **Configuração (Configuration) → Configuração geral (General configuration) → Editar (Edit)**, para acomodar a resposta em até 3000 ms exigida em testes (Requisito 3.4).

**✅ Validação:**
- O código foi **implantado (Deploy)** sem erros.
- Um teste rápido pela aba **Testar (Test)** com um evento simulando `GET /health` retorna HTTP 200 e o JSON de saúde.

**📸 Evidência / Print recomendado:** tela do editor com o `lambda_function.py` publicado e o resultado do teste `GET /health` (200).

---

## Fase 6 — Criar a REST API `api-waf-lab-sqli`

**Objetivo:** criar a **REST API** (não HTTP API) com endpoint regional (Requisitos 9.1, 9.3).

1. Abra **API Gateway** (na mesma `REGIAO`).
2. Clique em **Criar API (Create API)**.
3. Localize o cartão **REST API** (atenção: **não** escolha "REST API Private" nem "HTTP API") e clique em **Compilar (Build)**.

   > ⚠️ Deve ser **REST API**, e **não HTTP API** (Requisito 9.1). A REST API é necessária para associar a Web ACL do WAF diretamente ao stage e para Custom Domains regionais mapeados por stage.
4. Preencha:
   - **Nome da API (API name):** `api-waf-lab-sqli`.
   - **Tipo de endpoint (Endpoint type):** **Regional**.
5. Clique em **Criar API (Create API)**.

**✅ Validação:**
- A API `api-waf-lab-sqli` aparece com tipo de endpoint **Regional**.

**📸 Evidência / Print recomendado:** tela de configurações da API mostrando o nome `api-waf-lab-sqli` e o tipo de endpoint Regional.

---

## Fase 7 — Criar os recursos `{proxy+}` e a raiz `/` com método `ANY` (Lambda Proxy)

**Objetivo:** encaminhar **todas** as rotas para a Lambda usando `{proxy+}` + `ANY` e a raiz `/` + `ANY` (Requisitos 9.2, 9.3, 9.4).

### 7.1 — Recurso `{proxy+}` com método `ANY`

1. Na API `api-waf-lab-sqli`, selecione **Recursos (Resources)**.
2. Selecione o recurso raiz **`/`** e clique em **Criar recurso (Create resource)**.
3. Ative a opção **Recurso de proxy (Proxy resource)**. O **Nome do recurso (Resource name)** ficará `proxy` e o caminho `{proxy+}`.
4. Ative **Habilitar CORS (Enable CORS)** apenas se necessário (opcional para o laboratório).
5. Clique em **Criar recurso (Create resource)**.

   > 💡 **Comportamento observado no Console (importante):** ao ativar **CORS** na criação do recurso proxy, o Console **cria automaticamente** os métodos **`ANY`** e **`OPTIONS`** no `/{proxy+}`. Porém, o método **`ANY`** nasce com o **Tipo de integração** como **"Não configurado"** — será preciso **editá-lo** para apontar à Lambda (passo 6). O método **`OPTIONS`** já vem pronto como integração **Simulação (Mock)** para o CORS e pode ser mantido. Se você **não** ativar o CORS, o Console **não** cria os métodos automaticamente e você deve criar o método **`ANY`** manualmente (o passo 6 descreve os mesmos campos de integração).
6. Configure a integração do método **`ANY`** do `/{proxy+}`:
   - Se o `ANY` já existir como **"Não configurado"** (caso do CORS ativado), clique nele e escolha **Editar integração (Edit integration)**. Caso contrário, clique em **Criar método (Create method)** e escolha o método **`ANY`**.
   - **Tipo de integração (Integration type):** **Função Lambda (Lambda function)**.
   - Ative **Integração de proxy do Lambda (Lambda proxy integration)** (Requisito 9.2).
   - **Função Lambda (Lambda function):** selecione `waf-lab-sqli` na `REGIAO`.
7. Salve (**Criar método / Salvar (Save)**).
8. Quando solicitado, **conceda permissão** ao API Gateway para invocar a Lambda (o Console cria automaticamente a permissão de invocação — `lambda:InvokeFunction`). Confirme clicando em **OK / Conceder (Grant)**.
9. Confirme na lista de **Métodos** que o **`ANY`** passou a exibir **Tipo de integração: Lambda** (e não mais "Não configurado").

### 7.2 — Recurso raiz `/` com método `ANY`

> O `{proxy+}` **não** captura o caminho raiz. Por isso, a raiz `/` também recebe `ANY` para atender `GET /` (Requisito 5.1, decisão do design sobre `{proxy+}`).

1. Selecione o recurso raiz **`/`**.
2. Clique em **Criar método (Create method)** e escolha o método **`ANY`**.
   - **Tipo de integração (Integration type):** **Função Lambda (Lambda function)**.
   - Ative **Integração de proxy do Lambda (Lambda proxy integration)**.
   - **Função Lambda (Lambda function):** `waf-lab-sqli`.
3. Clique em **Criar método (Create method)** e conceda a permissão de invocação quando solicitado.

**✅ Validação:**
- Em **Recursos (Resources)**, existem o recurso raiz `/` com **`ANY`** e o recurso `/{proxy+}` com **`ANY`**, ambos apontando para a Lambda `waf-lab-sqli` no modo **Proxy**.

**📸 Evidência / Print recomendado:** árvore de **Recursos (Resources)** mostrando `/ → ANY` e `/{proxy+} → ANY` integrados à Lambda em modo Proxy.

---

## Fase 8 — Implantar (deploy) no stage `sem-waf`

**Objetivo:** criar o stage `sem-waf`, que permanecerá **sem** Web ACL (Requisitos 10.1, 10.3, 10.4).

> ⚠️ **Não confunda com o Deploy do Lambda.** O botão **Deploy** que aparece no editor de código da **função Lambda** publica apenas o **código** da Lambda (Fase 5). O deploy da **API** (criação do estágio) é feito no **API Gateway**, na tela de **Recursos (Resources)** da API `api-waf-lab-sqli`.

1. No **API Gateway**, abra a API `api-waf-lab-sqli` e vá em **Recursos (Resources)**.
2. Clique no botão laranja **Implantar API (Deploy API)** (canto superior direito). É o mesmo indicado pela mensagem "Reimplante sua API para que a atualização entre em vigor".
3. Abre a janela **Implantar API**. O campo **Estágio (Stage)** aparece **dentro dessa janela** (não fica solto na tela de Recursos). Em **Estágio (Stage)**, selecione **`*Novo estágio*` (New stage)**.
4. **Nome do estágio (Stage name):** `sem-waf`.
5. (Opcional) Descrição: "Ambiente sem WAF (grupo de controle)".
6. Clique em **Implantar (Deploy)**.
7. O estágio `sem-waf` passa a aparecer no menu lateral em **Estágios (Stages)**. Anote a **URL de invocação (Invoke URL)** do stage `sem-waf` (será usada em validações).

**✅ Validação:**
- O stage `sem-waf` existe e possui uma **URL de invocação (Invoke URL)**.
- Acesse `https://<invoke-url-sem-waf>/health` no navegador ou via `curl` → deve retornar HTTP 200 com o JSON de saúde.

**📸 Evidência / Print recomendado:** tela do stage `sem-waf` com a URL de invocação e o resultado 200 de `/health`.

---

## Fase 9 — Implantar (deploy) no stage `com-waf`

**Objetivo:** criar o stage `com-waf` sobre a **mesma** API e a **mesma** Lambda (Requisitos 10.2, 10.3).

1. Na API `api-waf-lab-sqli`, clique novamente em **Implantar API (Deploy API)**.
2. Em **Estágio (Stage)**, selecione **Novo estágio (New stage)**.
3. **Nome do estágio (Stage name):** `com-waf`.
4. (Opcional) Descrição: "Ambiente com WAF (grupo protegido)".
5. Clique em **Implantar (Deploy)**.
6. Anote a **URL de invocação (Invoke URL)** do stage `com-waf`.

> Neste momento, os dois stages têm comportamento **idêntico** — a Web ACL ainda **não** foi associada (isso ocorre na Fase 16). A única diferença entre `sem-waf` e `com-waf` será a presença do WAF (Requisito 10.3).

**✅ Validação:**
- Existem **dois** stages: `sem-waf` e `com-waf`, ambos sobre `api-waf-lab-sqli`.
- `https://<invoke-url-com-waf>/health` retorna HTTP 200 (ainda sem WAF).

**📸 Evidência / Print recomendado:** lista de stages da API mostrando `sem-waf` e `com-waf`.

---

## Fase 10 — Criar o Custom Domain `api-sem-waf.DOMINIO`

**Objetivo:** criar o Custom Domain regional para o ambiente sem WAF (Requisitos 12.1, 11).

1. No **API Gateway**, abra **Nomes de domínio personalizados (Custom domain names)**.
2. Clique em **Criar (Create)**.
3. Preencha:
   - **Nome de domínio (Domain name):** `api-sem-waf.DOMINIO`.
   - **Tipo de endpoint (Endpoint type):** **Regional**.
   - **Certificado ACM (ACM certificate):** selecione o certificado `*.DOMINIO` emitido na Fase 3.
   - **Política de segurança mínima de TLS (Minimum TLS version):** mantenha o padrão (TLS 1.2).
4. Clique em **Criar nome de domínio (Create domain name)**.
5. Após criado, anote o **Nome de domínio de destino do API Gateway (API Gateway domain name / target domain name)** regional — será usado no registro Alias do Route 53 (Fase 13).

**✅ Validação:**
- O Custom Domain `api-sem-waf.DOMINIO` foi criado com endpoint **Regional** e o certificado `*.DOMINIO` associado.

**📸 Evidência / Print recomendado:** tela do Custom Domain `api-sem-waf.DOMINIO` mostrando o tipo Regional, o certificado associado e o domínio de destino regional.

---

## Fase 11 — Criar o Custom Domain `api-com-waf.DOMINIO`

**Objetivo:** criar o Custom Domain regional para o ambiente com WAF (Requisitos 12.2, 11).

1. Em **Nomes de domínio personalizados (Custom domain names)**, clique em **Criar (Create)**.
2. Preencha:
   - **Nome de domínio (Domain name):** `api-com-waf.DOMINIO`.
   - **Tipo de endpoint (Endpoint type):** **Regional**.
   - **Certificado ACM (ACM certificate):** o mesmo certificado `*.DOMINIO`.
   - **TLS:** mantenha o padrão.
3. Clique em **Criar nome de domínio (Create domain name)**.
4. Anote o **domínio de destino regional (target domain name)** deste Custom Domain.

**✅ Validação:**
- O Custom Domain `api-com-waf.DOMINIO` foi criado com endpoint **Regional** e o mesmo certificado `*.DOMINIO` associado.

**📸 Evidência / Print recomendado:** tela do Custom Domain `api-com-waf.DOMINIO` com o domínio de destino regional.

---

## Fase 12 — Mapear os Custom Domains aos stages

**Objetivo:** ligar cada Custom Domain ao stage correto (Requisitos 12.3, 12.4).

### 12.1 — Mapear `api-sem-waf.DOMINIO` → stage `sem-waf`

1. Abra o Custom Domain **`api-sem-waf.DOMINIO`**.
2. Na aba **Mapeamentos de API (API mappings)**, clique em **Configurar mapeamentos de API (Configure API mappings)** → **Adicionar novo mapeamento (Add new mapping)**.
3. Preencha:
   - **API:** `api-waf-lab-sqli`.
   - **Estágio (Stage):** `sem-waf`.
   - **Caminho (Path):** deixe **vazio** (raiz).
4. Clique em **Salvar (Save)**.

### 12.2 — Mapear `api-com-waf.DOMINIO` → stage `com-waf`

1. Abra o Custom Domain **`api-com-waf.DOMINIO`**.
2. Em **Mapeamentos de API (API mappings)** → **Configurar mapeamentos de API (Configure API mappings)** → **Adicionar novo mapeamento (Add new mapping)**.
3. Preencha:
   - **API:** `api-waf-lab-sqli`.
   - **Estágio (Stage):** `com-waf`.
   - **Caminho (Path):** deixe **vazio**.
4. Clique em **Salvar (Save)**.

**✅ Validação:**
- `api-sem-waf.DOMINIO` mapeia para o stage `sem-waf`.
- `api-com-waf.DOMINIO` mapeia para o stage `com-waf`.

**📸 Evidência / Print recomendado:** tela de **Mapeamentos de API** de cada Custom Domain mostrando o stage correspondente.

---

## Fase 13 — Criar os registros Alias no Route 53

**Objetivo:** criar os registros DNS de Alias na zona hospedada existente (Requisitos 13.1, 13.2).

> 💡 **Sobre o "domínio de destino" (target domain name):** no campo de **Endpoint** do Alias, o Route 53 mostra o endereço interno do Custom Domain no formato **`d-xxxxxxxxxx.execute-api.REGIAO.amazonaws.com`**, e **não** o nome amigável `api-sem-waf.DOMINIO`. Isso é esperado. Para descobrir qual `d-...` pertence a cada Custom Domain, abra **API Gateway → Nomes de domínio personalizados → (o domínio) → campo Nome de domínio da API (API Gateway domain name)** e copie esse valor. Confirme que o `d-...` do registro `api-sem-waf` é o do Custom Domain `api-sem-waf.DOMINIO` (e não o do `api-com-waf`).
>
> 💡 **Avaliar integridade do destino (Evaluate target health):** para Alias de API Gateway com destino único, o recomendado é deixar **Não (No)**. Deixar **Sim** também funciona no laboratório, mas não é necessário.

### 13.1 — Registro `api-sem-waf`

1. Abra **Route 53 → Zonas hospedadas (Hosted zones) → DOMINIO**.
2. Clique em **Criar registro (Create record)**.
3. Preencha:
   - **Nome do registro (Record name):** `api-sem-waf`.
   - **Tipo (Record type):** **A**.
   - Ative **Alias (Alias)**.
   - **Rotear tráfego para (Route traffic to):** **Alias para API Gateway (Alias to API Gateway API)**.
   - **Região (Region):** selecione a `REGIAO`.
   - **Endpoint:** selecione o **domínio de destino regional** do Custom Domain `api-sem-waf.DOMINIO` (anotado na Fase 10).
4. Clique em **Criar registros (Create records)**.

### 13.2 — Registro `api-com-waf`

1. Ainda na zona `DOMINIO`, clique em **Criar registro (Create record)**.
2. Preencha:
   - **Nome do registro (Record name):** `api-com-waf`.
   - **Tipo (Record type):** **A**.
   - Ative **Alias (Alias)**.
   - **Rotear tráfego para (Route traffic to):** **Alias para API Gateway (Alias to API Gateway API)**.
   - **Região (Region):** `REGIAO`.
   - **Endpoint:** o **domínio de destino regional** do Custom Domain `api-com-waf.DOMINIO` (anotado na Fase 11).
3. Clique em **Criar registros (Create records)**.

> Se preferir, crie também os registros **AAAA** (IPv6) do mesmo modo. O Alias A já é suficiente para o laboratório.

**✅ Validação:**
- Aguarde a propagação DNS e teste no navegador ou via `curl`:
  - `https://api-sem-waf.DOMINIO/health` → HTTP 200 com JSON de saúde.
  - `https://api-com-waf.DOMINIO/health` → HTTP 200 (ainda sem WAF).

**📸 Evidência / Print recomendado:** tela do Route 53 mostrando os registros `api-sem-waf` e `api-com-waf` (tipo A, Alias) e os resultados 200 de `/health` em ambos os subdomínios.

---

## Fase 14 — Criar a Web ACL `waf-lab-sqli` com as regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab`

**Objetivo:** criar a Web ACL regional (ação padrão ALLOW), com as duas regras e a associação ao stage `com-waf` (Requisitos 14.1, 14.2, 14.3, 14.4, 14.5, 15, 16, 17.1, 17.2).

> 💡 **Interface observada no Console (importante):** o Console atual do AWS WAF usa o fluxo **"Criar pacote de proteção (ACL da Web)" (Create web ACL / protection pack)**, que é um pouco diferente do wizard clássico. Nele, o **Nome** e as **Regras** só são liberados **depois** de selecionar ao menos **um recurso** para proteger. Por isso, neste fluxo, associamos o stage `com-waf` **já na criação** (o que também cumpre a antiga "Fase 16"). O resultado final é o mesmo: Web ACL `waf-lab-sqli`, ação padrão ALLOW, 2 regras e associada **somente** ao `com-waf`.

### 14.1 — Iniciar a criação e selecionar o recurso

1. Abra **AWS WAF** → **Web ACLs** (ou **Pacotes de proteção / Protections**).
2. Confirme o **Escopo da região: Regional (Regional resources)** e selecione a `REGIAO`.

   > ⚠️ O escopo deve ser **Regional (REGIONAL)** (Requisito 14.2). **Não** use "CloudFront (Global)".
3. Clique em **Criar pacote de proteção (ACL da Web) (Create web ACL)**.
4. Em **Conte-nos sobre sua aplicação**:
   - **Categoria da aplicação:** selecione ao menos uma (ex.: **Outro / Other**) — campo **obrigatório**, apenas informativo.
   - **Foco da aplicação:** **API**.
5. Em **Selecione recursos para proteger**, clique em **Adicionar recursos (Add resources)**:
   - Escolha **Recursos regionais → API Gateway**.
   - Marque **apenas** `api-waf-lab-sqli - com-waf` (**API REST do Amazon API Gateway**).
   - ⚠️ **Não** marque `api-waf-lab-sqli - sem-waf` nem outros recursos (ex.: grupos de usuários do Cognito). O `sem-waf` é o grupo de controle e deve permanecer **sem** WAF (Requisitos 14.4, 14.5).
   - Clique em **Adicionar (Add)**.
6. Em **Escolher proteções iniciais**, selecione **"Crie seu próprio pacote usando todas as proteções oferecidas pelo AWS WAF" (Você o controla)**.
   - ⚠️ **Não** selecione "Regras recomendadas", "Regras essenciais" nem pacotes de regras gerenciadas da AWS. O laboratório usa **apenas** as 2 regras próprias.
7. Em **Nome e descrição** (liberado após selecionar o recurso):
   - **Nome (Name):** `waf-lab-sqli` (Requisito 14.1). *O nome não pode ser alterado depois.*

### 14.2 — Regra `Block-Fora-do-Brasil` (prioridade 1)

1. Em **Adicionar regras (Add rules)**, selecione o tipo **Regra baseada em localização geográfica (Geographic location)** e clique em **Seguinte (Next)**.

   > Também é possível usar **Regra personalizada (Custom rule)** e escolher a instrução geográfica manualmente; o resultado é o mesmo.
2. Preencha:
   - **Ação (Action):** **Block**.
   - **Nome da regra (Rule name):** `Block-Fora-do-Brasil` (Requisito 16.1).
   - **País (Country):** **Brasil (Brazil - BR)** (Requisito 16.2).
   - Em **Configuração de regras**, marque **Instrução de negação (NOT) — "Negar resultados da instrução"** para casar **somente** quando a origem for **diferente** de BR (Requisitos 16.2, 16.7).
   - **Endereço de IP para determinar a origem:** **Endereço de IP de origem (Source IP address)** (Requisito 16.3).
3. Clique em **Adicionar regra (Add rule)**.

### 14.3 — Regra `Block-SQLi-Lab` (prioridade 2)

1. Em **Adicionar regras (Add rules)**, selecione o tipo **Regra personalizada (Custom rule)** e clique em **Seguinte (Next)**.

   > A SQLi exige a **regra personalizada** (a de localização geográfica não serve).
2. Preencha:
   - **Ação (Action):** **Block** (Requisito 15.4).
   - **Nome da regra (Rule name):** `Block-SQLi-Lab` (Requisito 15.1).
   - **Se uma solicitação (If a request):** **corresponde à instrução (matches the statement)**.
   - **Inspecionar (Inspect):** **String de consulta (Query string)** (Requisito 15.2).
   - **Tipo de correspondência (Match type):** **Contém ataques de injeção de SQL (Contains SQL injection attacks)** (Requisito 15.2).
   - **Nível de sensibilidade (Sensitivity level):** **Baixo (Low)** é suficiente para o payload de teste (`1' OR '1'='1`); **Alto (High)** também funciona.
   - **Transformações de texto (Text transformations)** — adicione **nesta ordem** (Requisito 15.3):
     1. **Decodificar URL (URL_DECODE)**
     2. **Decodificação de entidade HTML (HTML_ENTITY_DECODE)**

     > A ordem importa: o item do **topo** da lista é aplicado **primeiro**. Não marque a negação (NOT) nesta regra.
3. Clique em **Adicionar regra (Add rule)**.

### 14.4 — Prioridade e ação padrão

1. Confirme a **ordem/prioridade** das regras (Requisitos 17.1, 17.2):
   - **Prioridade 1:** `Block-Fora-do-Brasil`
   - **Prioridade 2:** `Block-SQLi-Lab`
   - Se necessário, use **Mover para cima / Mover para baixo (Move up / Move down)**.
2. **Ação padrão da Web ACL (Default web ACL action):** **Permitir (Allow)** (Requisito 14.3).
3. Finalize clicando em **Criar pacote de proteção (ACL da Web) (Create web ACL)**.

**✅ Validação:**
- A Web ACL `waf-lab-sqli` existe com escopo **Regional** e ação padrão **Permitir (Allow)**.
- Contém exatamente **duas regras**, na ordem `Block-Fora-do-Brasil` (1) e `Block-SQLi-Lab` (2), ambas com ação **Block**; a geográfica com **NOT** para BR via **Source IP**; a SQLi com **SQL injection match** na **query string** e transformações **URL_DECODE → HTML_ENTITY_DECODE**.
- A Web ACL está associada a **exatamente 1 recurso**: o stage `com-waf`. O `sem-waf` tem **0** associações.

**📸 Evidência / Print recomendado:** tela final com o nome `waf-lab-sqli`, as duas regras com prioridades 1 e 2, a ação padrão Allow e o recurso associado `com-waf`.

---

## Fase 15 — (Referência) Regras e prioridade

> A criação das regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab` e a definição de prioridade foram feitas **dentro da Fase 14** (subitens 14.2, 14.3 e 14.4), por causa do fluxo "Criar pacote de proteção" do Console atual. Se você usar o **wizard clássico** do WAF (Web ACLs → Create web ACL, com etapas separadas de *Add rules* e *Set rule priority*), aplique os **mesmos** valores descritos em 14.2 a 14.4.

**Resumo das regras (para conferência):**

| Prioridade | Regra | Inspeção | Detalhes | Ação |
|---|---|---|---|---|
| 1 | `Block-Fora-do-Brasil` | Geo match | País **BR** com **NOT**, **Source IP** | Block |
| 2 | `Block-SQLi-Lab` | Query string | **SQL injection match**, transformações **URL_DECODE → HTML_ENTITY_DECODE** | Block |

Ação padrão da Web ACL: **Allow**.

---

## Fase 16 — Confirmar a associação ao stage `com-waf` (e conferir 0 associações no `sem-waf`)

**Objetivo:** garantir que a Web ACL está associada a **exatamente 1** recurso — o stage `com-waf` — e a **0** recursos no `sem-waf` (Requisitos 14.4, 14.5, 14.6).

> No fluxo "Criar pacote de proteção", a associação ao `com-waf` já foi feita na Fase 14 (subitem 14.1, passo 5). Esta fase serve para **confirmar** a associação. Se você usou o wizard clássico e ainda não associou, faça a associação aqui.

1. Em **AWS WAF → Web ACLs → `waf-lab-sqli`**, abra a aba **Recursos associados (Associated AWS resources)**.
2. **Confirme** que aparece **1 recurso**: o stage `com-waf` da API `api-waf-lab-sqli`.
3. Caso precise associar (wizard clássico) ou corrigir:
   - Clique em **Adicionar recurso associado (Add AWS resources)**.
   - **Tipo de recurso (Resource type):** **API Gateway**.
   - Selecione a API `api-waf-lab-sqli` e o **stage `com-waf`**. ⚠️ **Nunca** o `sem-waf` (Requisitos 14.4, 14.5).
   - Clique em **Adicionar (Add)**.
4. Se a associação falhar, o `com-waf` permanece sem proteção até ser refeita com sucesso — repita o passo (Requisito 14.6).

**✅ Validação:**
- A Web ACL `waf-lab-sqli` lista **1 recurso associado**: o stage `com-waf`.
- O stage `sem-waf` **não** aparece em nenhuma associação (0 associações).

**📸 Evidência / Print recomendado:** tela **Recursos associados (Associated AWS resources)** mostrando apenas o stage `com-waf`.

---
## Fase 17 — Testes de validação (comprovação sem WAF x com WAF)

**Objetivo:** comprovar, de forma prática e reproduzível, que a **única** diferença observável entre os dois ambientes é a presença do AWS WAF no stage `com-waf` (Requisitos 15.5, 15.6, 15.7, 18, 19, 16.5, 16.6, 16.7). Esta fase reúne todos os cenários de teste do laboratório — deve ser executada **após** a implantação (Fases 1 a 16) e **antes** da exclusão (Fase 18).

> **SQL Injection de teste:** `GET /produto?id=1' OR '1'='1`. Payload usado **apenas** para acionar a inspeção do WAF — a rota `/produto` apenas ecoa o parâmetro, **não** há vulnerabilidade real, **não** há banco de dados e **não** há execução de SQL.

### 17.0 — Convenções e recursos usados nos testes

Substitua `DOMINIO` pelo domínio de sua propriedade gerenciado na Zona Hospedada do Route 53.

| Item | Valor |
|---|---|
| Stage sem WAF | `sem-waf` |
| Stage com WAF | `com-waf` |
| Custom Domain sem WAF | `api-sem-waf.DOMINIO` (endpoint regional, mapeado ao stage `sem-waf`) |
| Custom Domain com WAF | `api-com-waf.DOMINIO` (endpoint regional, mapeado ao stage `com-waf`) |
| URL base sem WAF | `https://api-sem-waf.DOMINIO` |
| URL base com WAF | `https://api-com-waf.DOMINIO` |
| Web ACL | `waf-lab-sqli` (Regional, ação padrão ALLOW, associada somente ao `com-waf`) |
| Regra de geo (prioridade 1) | `Block-Fora-do-Brasil` (ação BLOCK) |
| Regra de SQLi (prioridade 2) | `Block-SQLi-Lab` (ação BLOCK) |
| Grupo de logs | CloudWatch Logs `/aws/lambda/{nome-da-funcao}` |
| Métrica de invocação | Namespace `AWS/Lambda`, métrica `Invocations` |

**Scripts de teste da API.** Os cenários podem ser executados com `curl` (comandos individuais) ou pelos scripts do laboratório, que executam o conjunto de requisições por ambiente:

```bash
# Python (multiplataforma)
python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf
python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf
```

```powershell
# PowerShell
./tests/test-sqli.ps1 -BaseUrl https://api-sem-waf.DOMINIO -Environment sem-waf
./tests/test-sqli.ps1 -BaseUrl https://api-com-waf.DOMINIO -Environment com-waf
```

Os scripts apresentam, para cada requisição, o endpoint testado, o código HTTP recebido, o esperado e o veredito (aprovado/reprovado), e retornam código de saída 0 somente se todos os testes forem aprovados.

> **Como ler cada cenário:** cada cenário indica **URL**, **comando**, **resultado esperado**, **código HTTP**, **onde verificar** e **evidência a coletar**.

---
## Cenário 1 — `sem-waf`: Health check (`/health`)

Confirma que a API e a Lambda respondem antes dos demais testes, no ambiente sem WAF.

- **URL:** `https://api-sem-waf.DOMINIO/health`
- **Comando (curl):**
  ```bash
  curl -i https://api-sem-waf.DOMINIO/health
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf` (teste "Health check").
- **Resultado esperado:** corpo JSON `{"status":"healthy","project":"AWS WAF Security Lab 03"}`.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script (linha de status e corpo).
- **Evidência a coletar:** print/log do comando mostrando `HTTP/1.1 200` e o corpo JSON.

---

## Cenário 2 — `sem-waf`: Rota de produto (`/produto`)

Confirma que a rota de eco responde 200 no ambiente sem WAF com um parâmetro simples.

- **URL:** `https://api-sem-waf.DOMINIO/produto?id=123`
- **Comando (curl):**
  ```bash
  curl -i "https://api-sem-waf.DOMINIO/produto?id=123"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf` (teste "Produto (parametro simples)").
- **Resultado esperado:** corpo JSON com o valor ecoado idêntico ao recebido, ex.: `{"id":"123"}`.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo `{"id":"123"}`.

---

## Cenário 3 — `sem-waf`: SQL Injection de teste processada (200)

Comprova que, **sem WAF**, a requisição com padrão de SQL Injection **alcança a Lambda** e é processada normalmente (a rota apenas ecoa o parâmetro).

- **URL:** `https://api-sem-waf.DOMINIO/produto?id=1' OR '1'='1`
- **Comando (curl):** (a query é codificada em URL)
  ```bash
  curl -i "https://api-sem-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf` (teste "SQL Injection de teste").
- **Resultado esperado:** a requisição é processada e o valor recebido é ecoado no campo `id` sem alteração; resposta em até 3000 ms.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script. A comprovação por CloudWatch é detalhada no Cenário 7.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo com o `id` ecoado. Anote o horário do envio para correlacionar com o CloudWatch (Cenário 7).

---

## Cenário 4 — `com-waf`: Health check (`/health`)

Confirma que o ambiente protegido responde normalmente a tráfego legítimo (do Brasil), sem bloqueio, na rota de health.

- **URL:** `https://api-com-waf.DOMINIO/health`
- **Comando (curl):**
  ```bash
  curl -i https://api-com-waf.DOMINIO/health
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf` (teste "Health check").
- **Resultado esperado:** corpo JSON `{"status":"healthy","project":"AWS WAF Security Lab 03"}`. Como a requisição não casa com nenhuma regra e a origem é o Brasil, a ação padrão ALLOW permite que ela alcance a API.
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo JSON.

> **Pré-condição:** executar a partir de uma origem **no Brasil**. A partir de fora do Brasil, a regra `Block-Fora-do-Brasil` retorna `403` (ver a seção de Geo-bloqueio ao final deste documento).

---

## Cenário 5 — `com-waf`: Rota de produto (`/produto`)

Confirma que uma requisição legítima à rota de eco, sem padrão de SQLi, é permitida (ALLOW) no ambiente protegido.

- **URL:** `https://api-com-waf.DOMINIO/produto?id=123`
- **Comando (curl):**
  ```bash
  curl -i "https://api-com-waf.DOMINIO/produto?id=123"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf` (teste "Produto (parametro simples)").
- **Resultado esperado:** corpo JSON com o valor ecoado, ex.: `{"id":"123"}`. A Web ACL permite a requisição (não há padrão de SQLi e a origem é o Brasil).
- **Código HTTP:** `200`.
- **Onde verificar:** saída do `curl`/script.
- **Evidência a coletar:** print mostrando `HTTP/1.1 200` e o corpo `{"id":"123"}`.

> **Pré-condição:** executar a partir de uma origem **no Brasil** (ver observação do Cenário 4).

---

## Cenário 6 — `com-waf`: SQL Injection de teste bloqueada (403)

Comprova que, **com WAF**, a requisição de SQL Injection de teste é **bloqueada pela regra `Block-SQLi-Lab`** antes de alcançar a API. Este é o cenário central do laboratório.

- **URL:** `https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1`
- **Comando (curl):** (a query é codificada em URL)
  ```bash
  curl -i "https://api-com-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script):** parte de `python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf` (teste "SQL Injection de teste").
- **Resultado esperado:** a Web ACL `waf-lab-sqli` bloqueia a requisição pela regra `Block-SQLi-Lab` (a origem no Brasil passa pela regra `Block-Fora-do-Brasil`, mas casa com a regra de SQLi de prioridade 2), respondendo em até 5 segundos e impedindo que a requisição alcance a API/Lambda.
- **Código HTTP:** `403`.
- **Onde verificar:** saída do `curl`/script; corpo típico de bloqueio do WAF (mensagem de "Forbidden"). A ausência de execução da Lambda é comprovada no Cenário 7; a evidência do WAF é coletada no Cenário 8 (e no Cenário 9).
- **Evidência a coletar:** print mostrando `HTTP/1.1 403`. Anote o horário do envio para correlacionar com o CloudWatch (Cenário 7) e com as Sampled requests (Cenário 8).

> **Pré-condição:** executar a partir de uma origem **no Brasil**. A partir de fora do Brasil o `403` também ocorreria, porém pela regra `Block-Fora-do-Brasil` (prioridade 1), e não pela regra de SQLi — ver a seção de Geo-bloqueio ao final.

---

## Cenário 7 — Verificação por CloudWatch: chegada (sem WAF) x bloqueio (com WAF) na Lambda

Comprova, por duas fontes independentes do CloudWatch da **mesma** Lambda, que a SQL Injection de teste **chega e executa** a Lambda no `sem-waf` e **não chega** no `com-waf`. Como os dois stages compartilham a mesma Lambda e o mesmo grupo de logs, a ausência de nova entrada e o incremento zero da métrica no `com-waf` provam que o WAF interrompeu a requisição **antes** da integração Lambda Proxy.

Realize este cenário logo após enviar a SQL Injection de teste nos Cenários 3 (`sem-waf`) e 6 (`com-waf`), correlacionando pelos horários anotados.

### 7.a — `sem-waf`: nova entrada de log e Invocations = 1

- **Envio (referência):** SQL Injection de teste pelo stage `sem-waf` (Cenário 3).
- **Onde verificar (logs):** CloudWatch Logs → grupo de logs `/aws/lambda/{nome-da-funcao}` → fluxo de log mais recente.
- **Resultado esperado (logs):** **nova entrada de execução** contendo o `requestId` (identificador de requisição), o método `GET` e o caminho `/produto`, dentro de uma janela de observação de **no mínimo 60 segundos** após o envio.
- **Onde verificar (métrica):** CloudWatch → Métricas → namespace `AWS/Lambda` → métrica `Invocations` da função, filtrada pelo horário do envio.
- **Resultado esperado (métrica):** `Invocations = 1` para essa requisição.
- **Evidência a coletar:** print da entrada de log destacando o `requestId`; print do gráfico/valor de `Invocations = 1`.

### 7.b — `com-waf`: ausência de nova entrada e Invocations = 0

- **Envio (referência):** SQL Injection de teste pelo stage `com-waf` (Cenário 6), que retornou `403`.
- **Onde verificar (logs):** mesmo grupo de logs `/aws/lambda/{nome-da-funcao}`.
- **Resultado esperado (logs):** **nenhuma nova entrada de execução** para essa requisição durante a janela de observação de **no mínimo 60 segundos** após o envio (a Lambda não executou porque o WAF bloqueou antes da integração).
- **Onde verificar (métrica):** namespace `AWS/Lambda`, métrica `Invocations`, filtrada pelo horário do envio.
- **Resultado esperado (métrica):** `Invocations = 0` (métrica inalterada) para essa requisição.
- **Evidência a coletar:** print do grupo de logs mostrando a ausência de nova entrada na janela de 60s; print de `Invocations = 0` no período.

### Resumo esperado da comprovação

| Cenário | Stage | HTTP | Nova entrada no log? | Invocations |
|---|---|---|---|---|
| SQL Injection de teste | `sem-waf` | 200 | Sim (com `requestId`) | 1 |
| SQL Injection de teste | `com-waf` (do Brasil) | 403 | Não | 0 |

### Critério de FALHA (janela de 60s)

Se a **entrada de execução esperada não for encontrada** no grupo de logs `/aws/lambda/{nome-da-funcao}` dentro da janela de observação de **60 segundos**, registre o resultado da verificação como **FALHA**, indicando:

- o **stage** avaliado (`sem-waf` ou `com-waf`);
- o **`requestId`** esperado (ausente).

Aplica-se, por exemplo, ao caso 7.a: se a nova entrada com o `requestId` do envio pelo `sem-waf` não aparecer em 60s, o cenário é uma **FALHA** (a comprovação de chegada à Lambda não foi obtida).

---

## Cenário 8 — Evidências de bloqueio nas Sampled requests do WAF

Coleta a evidência do bloqueio na própria ferramenta, consultando as Solicitações de amostra (Sampled requests) da Web ACL.

- **Onde verificar:** Console do AWS WAF → Web ACLs → `waf-lab-sqli` → aba de **Solicitações de amostra (Sampled requests)** (é possível filtrar por regra e período; correlacione pelo horário do envio no Cenário 6).
- **Resultado esperado:** a amostra da SQL Injection de teste enviada pelo `com-waf` deve mostrar:
  - a **regra que correspondeu**: `Block-SQLi-Lab`;
  - a **ação**: `BLOCK`;
  - a **origem** (Source IP) da requisição;
  - o **código HTTP** associado ao bloqueio: `403`.
- **Evidência a coletar:** print da linha de amostra destacando `Block-SQLi-Lab`, ação `BLOCK`, a origem e o `403`.

> Observação: as Sampled requests dependem de a Web ACL estar coletando amostras no período consultado. Envie a SQL Injection de teste (Cenário 6) e consulte a amostra em seguida, filtrando pelo intervalo do envio.

---

## Cenário 9 — Consolidação e comparação entre ambientes

Fecha a comparação didática consolidando os resultados dos cenários anteriores, deixando explícita a única diferença observável entre os ambientes: a presença do WAF no `com-waf`.

- **Comando (execução consolidada dos scripts):**
  ```bash
  python tests/test-sqli.py --base-url https://api-sem-waf.DOMINIO --env sem-waf
  python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf
  ```
  ou, em PowerShell:
  ```powershell
  ./tests/test-sqli.ps1 -BaseUrl https://api-sem-waf.DOMINIO -Environment sem-waf
  ./tests/test-sqli.ps1 -BaseUrl https://api-com-waf.DOMINIO -Environment com-waf
  ```
- **Resultado esperado (tabela consolidada):**

  | # | Requisição | Stage | HTTP esperado |
  |---|---|---|---|
  | 1 | `GET /health` | `sem-waf` | 200 |
  | 2 | `GET /produto?id=123` | `sem-waf` | 200 |
  | 3 | SQL Injection de teste | `sem-waf` | 200 |
  | 4 | `GET /health` | `com-waf` | 200 |
  | 5 | `GET /produto?id=123` | `com-waf` | 200 |
  | 6 | SQL Injection de teste | `com-waf` | 403 (`Block-SQLi-Lab`) |

- **Código HTTP:** conforme a tabela acima (a única inversão de comportamento entre os stages é a SQL Injection de teste: `200` no `sem-waf` e `403` no `com-waf`).
- **Onde verificar:** saída dos scripts (resumo com veredito e código de saída) somada às evidências dos Cenários 7 (CloudWatch) e 8 (Sampled requests).
- **Evidência a coletar:** print do resumo dos scripts (todos aprovados por ambiente) e a tabela consolidada acima preenchida com os resultados reais observados. Reúna, no mesmo conjunto de evidências, os prints do CloudWatch (Cenário 7) e das Sampled requests (Cenário 8) para comprovar que o `403` do `com-waf` foi gerado pelo WAF antes da Lambda.

---

## Seção de Geo-bloqueio — Regra `Block-Fora-do-Brasil`

Esta seção é dedicada ao teste da **restrição geográfica** do ambiente protegido (stage `com-waf`). A regra `Block-Fora-do-Brasil` (prioridade 1 na Web ACL `waf-lab-sqli`) usa correspondência geográfica com o país **BR** (ISO 3166-1 alpha-2) e **lógica de negação (NOT)**: ela casa (e aplica `BLOCK`) sempre que a origem for **diferente do Brasil**. Como é a **primeira** regra avaliada, requisições de fora do Brasil são bloqueadas **antes** da inspeção de SQL Injection (regra `Block-SQLi-Lab`, prioridade 2).

> **Escopo:** o Geo-bloqueio só existe no stage `com-waf` (única associação da Web ACL). O stage `sem-waf` não possui WAF e, portanto, não aplica restrição geográfica.

### Como a AWS determina a origem geográfica

- A origem geográfica é determinada pela **AWS** a partir do **endereço de origem (Source IP address)** da requisição, mapeado para o país correspondente. Não há como (nem se deve) **forjar** a origem: o teste consiste em executar a requisição a partir de uma rede/host realmente localizado no país desejado.
- **Para testar a partir do Brasil:** basta executar de uma conexão/host localizada no Brasil (o caso comum de quem implanta o laboratório no país).
- **Para testar a partir de fora do Brasil**, use uma origem cujo Source IP esteja fora do país, por exemplo:
  - uma **VPN** com ponto de saída em outro país;
  - uma **instância/host em outra região** da AWS ou de outro provedor (ex.: uma EC2 em `us-east-1`) executando o `curl`/script;
  - qualquer outra rede comprovadamente fora do Brasil.
- **País de origem indeterminado:** quando a AWS **não consegue determinar** o país a partir do Source IP, a requisição é tratada como **fora do Brasil** e recebe `BLOCK` (postura conservadora, *fail-closed*). Ver o cenário G.3.

### Modo geográfico dos scripts de teste

Os scripts do laboratório possuem um **modo geográfico** que executa o conjunto de requisições a partir das duas origens e apresenta os resultados em **blocos separados e identificados** (origem no Brasil e origem fora do Brasil):

```bash
# Python (multiplataforma)
python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf --geo
```

```powershell
# PowerShell (equivalente)
./tests/test-sqli.ps1 -BaseUrl https://api-com-waf.DOMINIO -Environment com-waf -Geo
```

> **Importante:** o modo `--geo`/`-Geo` **não forja** a origem. Ele apenas organiza a saída em dois blocos rotulados; a origem efetiva depende de **onde o script está sendo executado**. Para obter o bloco "fora do Brasil", execute o script de um host/rede fora do país (ex.: instância em outra região ou VPN). O ideal é rodar o script duas vezes — uma de dentro do Brasil e outra de fora — e reunir os dois blocos como evidência.

---

## Cenário G.1 — `com-waf` do Brasil: comportamento normal (origem que passa pela Regra_Geo)

Comprova que, para uma origem **no Brasil**, a regra `Block-Fora-do-Brasil` **não** aplica `BLOCK` e a Web ACL prossegue para as demais regras: o tráfego legítimo responde `200` e apenas a SQL Injection de teste é bloqueada (pela regra de SQLi, e não pela geográfica).

- **Origem:** rede/host **no Brasil**.
- **URLs / requisições:**
  - `https://api-com-waf.DOMINIO/health` → `200`
  - `https://api-com-waf.DOMINIO/produto?id=123` → `200`
  - SQL Injection de teste: `https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1` → `403` (pela regra `Block-SQLi-Lab`, prioridade 2)
- **Comando (curl):**
  ```bash
  curl -i https://api-com-waf.DOMINIO/health
  curl -i "https://api-com-waf.DOMINIO/produto?id=123"
  curl -i "https://api-com-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script — bloco "origem no Brasil"):**
  ```bash
  python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf --geo
  ```
  (executado a partir de uma origem no Brasil; observe o bloco identificado como **origem no Brasil**).
- **Resultado esperado:** `/health` e `/produto?id=123` retornam `200`; a SQL Injection de teste retorna `403` pela regra `Block-SQLi-Lab`. A regra `Block-Fora-do-Brasil` **não** casa (origem = BR) e deixa a avaliação prosseguir.
- **Código HTTP:** `200` (rotas legítimas) e `403` (SQL Injection de teste, pela regra de SQLi).
- **Onde verificar:** saída do `curl`/script (bloco "origem no Brasil"); a distinção da regra que causou o `403` é confirmada nas Sampled requests (ver G.4).
- **Evidência a coletar:** print do bloco "origem no Brasil" mostrando `200` nas rotas legítimas e `403` na SQL Injection de teste; anote o horário para correlacionar com as Sampled requests (regra `Block-SQLi-Lab`).

---

## Cenário G.2 — `com-waf` de fora do Brasil: bloqueio pela regra `Block-Fora-do-Brasil` (403)

Comprova que, para uma origem **fora do Brasil**, **qualquer** requisição ao stage `com-waf` é bloqueada com `403` pela regra `Block-Fora-do-Brasil` (prioridade 1), **antes** da inspeção de SQL Injection. Mesmo requisições legítimas (ex.: `/health`, `/produto?id=123`) são bloqueadas, porque a barreira geográfica é a primeira a ser avaliada.

- **Origem:** rede/host **fora do Brasil** (ex.: VPN com saída em outro país ou instância em outra região). A origem **não** é forjada.
- **URLs / requisições (todas bloqueadas):**
  - `https://api-com-waf.DOMINIO/health` → `403`
  - `https://api-com-waf.DOMINIO/produto?id=123` → `403`
  - SQL Injection de teste: `https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1` → `403` (também pela regra geográfica, pois é avaliada antes da SQLi)
- **Comando (curl, executado de fora do Brasil):**
  ```bash
  curl -i https://api-com-waf.DOMINIO/health
  curl -i "https://api-com-waf.DOMINIO/produto?id=123"
  curl -i "https://api-com-waf.DOMINIO/produto?id=1%27%20OR%20%271%27%3D%271"
  ```
- **Comando (script — bloco "origem fora do Brasil"):**
  ```bash
  python tests/test-sqli.py --base-url https://api-com-waf.DOMINIO --env com-waf --geo
  ```
  (executado a partir de uma origem fora do Brasil; observe o bloco identificado como **origem fora do Brasil**).
- **Resultado esperado:** **todas** as requisições são bloqueadas com `403` pela regra `Block-Fora-do-Brasil`. A requisição **não** alcança a REST API nem a Lambda (sem execução, sem nova entrada de log, `Invocations` inalterado). A inspeção de SQLi **não** chega a ser aplicada, pois a regra geográfica (prioridade 1) já bloqueou.
- **Código HTTP:** `403` (todas as requisições), gerado pelo próprio WAF.
- **Onde verificar:** saída do `curl`/script (bloco "origem fora do Brasil"); a regra que causou o bloqueio é confirmada nas Sampled requests (ver G.4). A ausência de execução da Lambda pode ser confirmada no CloudWatch, de forma análoga ao Cenário 7 (`Invocations = 0`, sem nova entrada de log).
- **Evidência a coletar:** print do bloco "origem fora do Brasil" mostrando `403` em todas as requisições; anote o horário e a origem (país/IP de saída da VPN ou região da instância) para correlacionar com as Sampled requests (regra `Block-Fora-do-Brasil`).

---

## Cenário G.3 — País de origem indeterminado: tratado como fora do Brasil (403)

Comprova o comportamento *fail-closed* da regra geográfica: quando a AWS **não consegue determinar** o país a partir do Source IP, a requisição é tratada como **fora do Brasil** e recebe `BLOCK` (`403`) pela regra `Block-Fora-do-Brasil` (Requisito 16.7).

- **Origem:** rede/host cujo Source IP **não** é mapeável para um país (origem indeterminada). Este caso pode não ser facilmente reproduzível de forma controlada; quando ocorrer, o comportamento esperado é o descrito abaixo.
- **URLs / requisições:** mesmas do Cenário G.2 — qualquer requisição ao stage `com-waf`.
- **Resultado esperado:** a requisição é tratada como **fora do Brasil** e bloqueada com `403` pela regra `Block-Fora-do-Brasil`, sem alcançar a REST API/Lambda.
- **Código HTTP:** `403` (pela regra `Block-Fora-do-Brasil`).
- **Onde verificar:** saída do `curl`/script e Sampled requests do WAF (regra `Block-Fora-do-Brasil`, ação `BLOCK`).
- **Evidência a coletar:** quando reproduzível, print da amostra mostrando o bloqueio pela regra `Block-Fora-do-Brasil` para a origem sem país determinado; caso não seja possível reproduzir, documente que o comportamento esperado é o mesmo do Cenário G.2 (tratamento como fora do Brasil, `403`).

---

## Cenário G.4 — Evidências de Geo-bloqueio nas Sampled requests do WAF

Coleta a evidência do bloqueio geográfico na própria ferramenta, consultando as Solicitações de amostra (Sampled requests) da Web ACL, de forma análoga ao Cenário 8 (que trata do bloqueio por SQLi).

- **Onde verificar:** Console do AWS WAF → Web ACLs → `waf-lab-sqli` → aba de **Solicitações de amostra (Sampled requests)** (é possível filtrar por regra e período; correlacione pelo horário do envio no Cenário G.2).
- **Resultado esperado:** a amostra da requisição enviada de **fora do Brasil** deve mostrar:
  - a **regra que correspondeu**: `Block-Fora-do-Brasil`;
  - a **ação**: `BLOCK`;
  - a **origem** (Source IP) da requisição, fora do Brasil;
  - o **código HTTP** associado ao bloqueio: `403`.
- **Evidência a coletar:** print da linha de amostra destacando `Block-Fora-do-Brasil`, ação `BLOCK`, a origem (Source IP fora do Brasil) e o `403`.

> Observação: as Sampled requests dependem de a Web ACL estar coletando amostras no período consultado. Envie as requisições de fora do Brasil (Cenário G.2) e consulte a amostra em seguida, filtrando pelo intervalo do envio.

---

## Resumo esperado do Geo-bloqueio

| Origem | Requisição | Stage | HTTP | Regra que bloqueia |
|---|---|---|---|---|
| Brasil | `GET /health` | `com-waf` | 200 | — (ALLOW) |
| Brasil | `GET /produto?id=123` | `com-waf` | 200 | — (ALLOW) |
| Brasil | SQL Injection de teste | `com-waf` | 403 | `Block-SQLi-Lab` (prioridade 2) |
| Fora do Brasil | `GET /health` | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Fora do Brasil | `GET /produto?id=123` | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Fora do Brasil | SQL Injection de teste | `com-waf` | 403 | `Block-Fora-do-Brasil` (prioridade 1) |
| Indeterminada | qualquer requisição | `com-waf` | 403 | `Block-Fora-do-Brasil` (tratada como fora do Brasil) |

A comparação evidencia o efeito da **ordem das regras**: do Brasil, a barreira geográfica é transparente e apenas a SQLi é bloqueada (pela regra de prioridade 2); de fora do Brasil, **tudo** é bloqueado já na regra geográfica (prioridade 1), antes da inspeção de SQLi.

---

## Fase 18 — Exclusão completa dos recursos (limpeza / teardown)

**Objetivo:** remover **todos** os recursos do laboratório respeitando as **dependências** entre eles, para evitar custos e deixar a conta limpa (Requisitos 24.5, 26.1).

> ⚠️ **Ordem importa.** A remoção segue a ordem inversa das dependências: primeiro desassociamos e removemos a proteção do WAF, depois o DNS, em seguida os Custom Domains e a API, então a Lambda e, **por último**, o certificado ACM (que fica preso enquanto estiver em uso por algum Custom Domain). Seguir a ordem abaixo evita erros de "recurso em uso (resource in use)".
>
> 💡 **Confirme a `REGIAO`.** Todos os recursos regionais (WAF, API Gateway, Custom Domains, ACM) devem ser excluídos na **mesma** `REGIAO` em que foram criados. Verifique o seletor de região antes de começar.

### 18.1 — Desassociar e excluir a Web ACL `waf-lab-sqli` e suas regras

**Por quê primeiro:** enquanto a Web ACL estiver **associada** ao stage `com-waf`, ela não pode ser excluída. A desassociação também restaura o comportamento do `com-waf` para "sem proteção".

1. Abra **AWS WAF → Web ACLs**, confirme o escopo **Recursos regionais (Regional resources)** e a `REGIAO`.
2. Clique na Web ACL **`waf-lab-sqli`**.
3. Abra a aba **Recursos associados (Associated AWS resources)**.
4. Selecione o stage **`com-waf`** (API `api-waf-lab-sqli`) e clique em **Desassociar (Disassociate)**. Confirme.

   > As regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab` estão **contidas** na Web ACL, portanto serão removidas junto com ela — não é necessário excluí-las separadamente. Se você tiver criado essas regras como **grupos de regras (rule groups)** reutilizáveis (não é o caso deste laboratório, que usa regras próprias na Web ACL), exclua-os depois em **AWS WAF → Grupos de regras (Rule groups)**.
5. Volte à lista **Web ACLs**, marque **`waf-lab-sqli`** e clique em **Excluir (Delete)**.
6. Confirme a exclusão digitando o nome, se solicitado, e clique em **Excluir (Delete)**.

**✅ Validação:**
- A aba **Recursos associados** de `waf-lab-sqli` não lista mais o stage `com-waf` (0 associações) **antes** da exclusão.
- A Web ACL `waf-lab-sqli` **não** aparece mais na lista de Web ACLs regionais da `REGIAO`.
- (Opcional) `GET https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1` volta a retornar **HTTP 200** (sem WAF), confirmando a desassociação.

**📸 Evidência / Print recomendado:** tela de **Recursos associados** já sem o `com-waf` e a lista de Web ACLs sem `waf-lab-sqli`.

---

### 18.2 — Excluir os registros Alias do Route 53 (`api-sem-waf`, `api-com-waf`)

**Por quê agora:** os registros DNS apontam para os Custom Domains. Removê-los antes dos Custom Domains evita apontamentos órfãos.

1. Abra **Route 53 → Zonas hospedadas (Hosted zones) → DOMINIO**.
2. Localize e selecione o registro **`api-sem-waf`** (Tipo **A**, Alias).
3. Clique em **Excluir registro (Delete record)** e confirme em **Excluir (Delete)**.
4. Repita para o registro **`api-com-waf`** (Tipo **A**, Alias).
5. Se você criou registros **AAAA** (IPv6) para esses subdomínios, exclua-os também.

> ⚠️ **Não** exclua o registro **CNAME de validação do ACM** neste momento — ele será tratado (opcionalmente) na Fase 18.6, após a exclusão do certificado. E **nunca** exclua os registros **NS** e **SOA** da zona hospedada.

**✅ Validação:**
- Os registros `api-sem-waf` e `api-com-waf` **não** aparecem mais na zona hospedada de `DOMINIO`.
- (Opcional, após propagação) `https://api-sem-waf.DOMINIO/health` e `https://api-com-waf.DOMINIO/health` deixam de resolver.

**📸 Evidência / Print recomendado:** tela do Route 53 mostrando a zona `DOMINIO` sem os registros `api-sem-waf` e `api-com-waf`.

---

### 18.3 — Excluir os mapeamentos e os Custom Domains `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO`

**Por quê agora:** os Custom Domains **usam** o certificado ACM e mapeiam para os stages. É preciso removê-los **antes** de excluir o certificado (Fase 18.6) e antes de excluir a API/stages (Fase 18.4).

1. No **API Gateway**, abra **Nomes de domínio personalizados (Custom domain names)**.
2. Abra o Custom Domain **`api-sem-waf.DOMINIO`**.
3. Na aba **Mapeamentos de API (API mappings)**, remova o mapeamento para o stage `sem-waf`: clique em **Configurar mapeamentos de API (Configure API mappings)**, remova a linha do mapeamento e clique em **Salvar (Save)**.
4. Volte à lista de Custom Domains, selecione **`api-sem-waf.DOMINIO`** e clique em **Excluir (Delete)**. Confirme.
5. Repita os passos 2 a 4 para o Custom Domain **`api-com-waf.DOMINIO`** (removendo o mapeamento para o stage `com-waf` e, em seguida, excluindo o domínio).

**✅ Validação:**
- Nenhum dos Custom Domains `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO` aparece mais na lista de **Nomes de domínio personalizados**.

**📸 Evidência / Print recomendado:** tela de **Nomes de domínio personalizados** vazia (ou sem os dois domínios do laboratório).

---

### 18.4 — Excluir os stages (`sem-waf`, `com-waf`) e a REST API `api-waf-lab-sqli`

**Por quê agora:** com os Custom Domains e o WAF já removidos, a API e seus stages podem ser excluídos sem dependências pendentes.

> 💡 Excluir a **REST API** inteira remove automaticamente seus stages, recursos, métodos e deploys. Se preferir apenas remover os stages e manter a API, use o passo opcional a seguir; caso contrário, vá direto para a exclusão da API.

1. (Opcional) Excluir stages individualmente:
   - No **API Gateway**, abra a API **`api-waf-lab-sqli`** → **Estágios (Stages)**.
   - Selecione o stage **`com-waf`** e clique em **Excluir (Delete)**. Confirme.
   - Repita para o stage **`sem-waf`**.
2. Excluir a REST API completa:
   - Em **API Gateway**, localize a API **`api-waf-lab-sqli`**.
   - Abra a API e use **Ações da API (API actions) → Excluir API (Delete API)** (ou selecione a API na lista e clique em **Excluir (Delete)**).
   - Confirme digitando o nome da API, se solicitado, e clique em **Excluir (Delete)**.

**✅ Validação:**
- A API **`api-waf-lab-sqli`** e seus stages `sem-waf` e `com-waf` **não** aparecem mais no API Gateway da `REGIAO`.

**📸 Evidência / Print recomendado:** lista de APIs do API Gateway sem a `api-waf-lab-sqli`.

---

### 18.5 — Excluir a função Lambda `waf-lab-sqli` (e, opcionalmente, o grupo de logs)

**Por quê agora:** a Lambda só era invocada pela API, que já foi removida. Não há mais dependências.

1. Abra **Lambda** (na `REGIAO`).
2. Selecione a função **`waf-lab-sqli`**.
3. Clique em **Ações (Actions) → Excluir (Delete)** (ou **Excluir função / Delete function**). Confirme digitando `delete`/o nome, se solicitado.

**Grupo de logs do CloudWatch (opcional):**

4. Abra **CloudWatch → Grupos de logs (Log groups)**.
5. Localize o grupo **`/aws/lambda/waf-lab-sqli`** (padrão `/aws/lambda/{nome-da-funcao}`).
6. Selecione o grupo e clique em **Ações (Actions) → Excluir (Delete)**. Confirme.

   > A exclusão do grupo de logs é **opcional** — mantê-lo preserva as evidências (por exemplo, os `requestId` usados nos testes do `sem-waf`). Excluí-lo evita cobrança de retenção de logs.

**Função de execução IAM (opcional):**

7. Se você quiser limpar também a **função IAM (execution role)** criada automaticamente para a Lambda, abra **IAM → Funções (Roles)**, localize a role associada (nome geralmente iniciado por `waf-lab-sqli-role-...`) e exclua-a **somente** se não estiver em uso por outros recursos.

**✅ Validação:**
- A função **`waf-lab-sqli`** não aparece mais na lista do Lambda.
- (Se excluído) o grupo de logs `/aws/lambda/waf-lab-sqli` não aparece mais no CloudWatch.

**📸 Evidência / Print recomendado:** lista do Lambda sem a função `waf-lab-sqli` (e, se aplicável, a lista de grupos de logs sem `/aws/lambda/waf-lab-sqli`).

---

### 18.6 — Excluir o certificado ACM `*.DOMINIO` (por último) e o CNAME de validação

**Por quê por último:** o certificado só pode ser excluído quando **não** estiver mais **em uso** por nenhum Custom Domain (removidos na Fase 18.3). Tentar excluí-lo antes resulta em erro de "certificado em uso (in use)".

1. Abra **Certificate Manager (ACM)** na `REGIAO`.
2. Localize o certificado **`*.DOMINIO`** (curinga).
3. Confirme que o campo **Em uso (In use)** / **Recursos associados (Associated resources)** está **vazio**. Se ainda aparecer algum recurso, volte e conclua a Fase 18.3.
4. Selecione o certificado e clique em **Excluir (Delete)**. Confirme.
5. **(Opcional) Registro CNAME de validação:** o certificado foi validado por DNS na Fase 3, o que criou um registro **CNAME** na zona hospedada de `DOMINIO`. Após excluir o certificado, esse CNAME de validação fica obsoleto:
   - Abra **Route 53 → Zonas hospedadas → DOMINIO**.
   - Localize o registro **CNAME** de validação do ACM (nome no formato `_<hash>.DOMINIO` apontando para `*.acm-validations.aws`).
   - Selecione-o e clique em **Excluir registro (Delete record)** e confirme.

   > Este passo é **opcional**; deixar o CNAME de validação não gera custo, mas removê-lo mantém a zona hospedada limpa.

**✅ Validação:**
- O certificado `*.DOMINIO` **não** aparece mais na lista do ACM da `REGIAO`.
- (Se excluído) o CNAME de validação do ACM não aparece mais na zona hospedada de `DOMINIO`.

**📸 Evidência / Print recomendado:** lista do ACM sem o certificado `*.DOMINIO` e, se aplicável, a zona do Route 53 sem o CNAME de validação.

---

### 18.7 — Checklist final de limpeza

Confirme, ao final, que **todos** os recursos do laboratório foram removidos (Requisitos 24.5, 26.1):

- [ ] Web ACL `waf-lab-sqli` desassociada do `com-waf` e **excluída** (com as regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab`).
- [ ] Registros Alias `api-sem-waf` e `api-com-waf` (A/AAAA) **excluídos** do Route 53.
- [ ] Custom Domains `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO` (com seus mapeamentos) **excluídos**.
- [ ] Stages `sem-waf` e `com-waf` e a REST API `api-waf-lab-sqli` **excluídos**.
- [ ] Função Lambda `waf-lab-sqli` **excluída** (grupo de logs `/aws/lambda/waf-lab-sqli` opcionalmente excluído).
- [ ] Certificado ACM `*.DOMINIO` **excluído** (CNAME de validação opcionalmente removido do Route 53).
- [ ] Preservados a **zona hospedada (Hosted zone)** de `DOMINIO` e seus registros **NS**/**SOA**.

> ✅ Após concluir este checklist, o laboratório está totalmente removido e não deve gerar custos remanescentes (exceto a cobrança fixa da zona hospedada do Route 53, que **não** faz parte deste laboratório e deve ser mantida).
