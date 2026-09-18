# Guia de Implantação Manual — AWS WAF Security Lab 03 (SQL Injection)
![Descrição da imagem](<imagens/imagem%20(1).png>)
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

![Descrição da imagem](<imagens/imagem%20(2).png>)

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
15. (Referência) Regras e prioridade
16. Confirmar a associação ao stage `com-waf`

> **Testes e exclusão em documentos separados:** após concluir as fases de implantação (1 a 16), siga para os **testes de validação** em [`TESTES.md`](./TESTES.md) e, ao final do laboratório, para a **exclusão completa dos recursos** em [`EXCLUSAO.md`](./EXCLUSAO.md).

--- Exclusão completa dos recursos (limpeza / teardown)

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

![Descrição da imagem](<imagens/imagem%20(21).png>)

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

![Descrição da imagem](<imagens/imagem%20(22).png>)

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

![Descrição da imagem](<imagens/imagem%20(23).png>)

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

![Descrição da imagem](<imagens/imagem%20(24).png>)

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

![Descrição da imagem](<imagens/imagem%20(28).png>)

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

![Descrição da imagem](<imagens/imagem%20(25).png>)

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

![Descrição da imagem](<imagens/imagem%20(25).png>)

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

![Descrição da imagem](<imagens/imagem%20(26).png>)
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

![Descrição da imagem](<imagens/imagem%20(29).png>)
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

![Descrição da imagem](<imagens/imagem%20(30).png>)

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

![Descrição da imagem](<imagens/imagem%20(27).png>)

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

## Próximos passos

Concluídas as Fases 1 a 16, a infraestrutura do laboratório está implantada. Prossiga para:

- **Testes de validação** — comprovação prática do comportamento sem WAF x com WAF (cenários de SQLi e geo-bloqueio, evidências no CloudWatch e nas Sampled requests): [`TESTES.md`](./TESTES.md).
- **Exclusão / teardown** — remoção completa de todos os recursos, na ordem correta de dependências, para evitar custos: [`EXCLUSAO.md`](./EXCLUSAO.md).
