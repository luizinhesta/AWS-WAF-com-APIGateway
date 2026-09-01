# Prompt para o Kiro — Correção da documentação do AWS WAF Lab 01

Revisar e corrigir toda a documentação do projeto `aws-waf-lab-01-xss` com base na implantação real já validada no AWS Console.

Não recrie a documentação do zero e não remova conteúdo válido. Preserve a estrutura e o estilo didático existentes, mas corrija inconsistências, etapas ausentes, comandos problemáticos e informações que não correspondem mais ao ambiente implantado.

Os arquivos que devem ser revisados são:

- `README.md`
- `ARQUITETURA.md`
- `IMPLANTACAO.md`
- `TESTE.md`

A implantação real e validada possui atualmente:

- Bucket S3 privado.
- Duas distribuições CloudFront:
  - `site-sem-waf.dev.inhesta.net`
  - `site-com-waf.dev.inhesta.net`
- Web ACL:
  - `waf-lab-xss`
- Regra 1:
  - `Block-XSS-Lab`
- Regra 2:
  - `Block-Fora-do-Brasil`
- Resposta HTML personalizada para o bloqueio geográfico.

---

# 1. CORRIGIR A REGRA DE XSS NA IMPLANTAÇÃO

No `IMPLANTACAO.md`, deixe a criação da regra `Block-XSS-Lab` extremamente explícita.

A configuração correta e validada é:

**Ação**

`Block`

**Nome**

`Block-XSS-Lab`

**Se uma solicitação**

`corresponde à instrução`

**Inspecionar**

`Todos os parâmetros de consulta`

**Tipo de correspondência**

`Contém ataques de injeção de XSS`

**Pre-parse text transformations**

Não configurar nenhuma transformação.

**Text transformations / Transformação de texto**

Selecionar obrigatoriamente:

`Decodificar URL`

ou:

`URL_DECODE`

Destaque na documentação com uma observação de atenção:

> IMPORTANTE: não deixar a transformação como `Nenhum`. Durante a validação real do laboratório, a regra permaneceu retornando HTTP 200 para o payload XSS enquanto a transformação estava configurada como `Nenhum`. Depois da alteração para `Decodificar URL`, o mesmo teste passou a retornar `403 BLOCKED`.

Explique que o payload gerado pelo laboratório pode chegar codificado, por exemplo:

`%3Cscript%3Ealert(1)%3C%2Fscript%3E`

e que `URL_DECODE` permite ao WAF analisar o conteúdo decodificado.

Depois de salvar a regra, adicionar uma pequena validação obrigatória:

- Requisição normal COM WAF → `200`
- Requisição XSS COM WAF → `403`

Não avançar para considerar a regra concluída enquanto esse comportamento não estiver validado.

---

# 2. ADICIONAR A REGRA GEOGRÁFICA AO IMPLANTACAO.md

A documentação original não possui a implantação completa da regra geográfica. Acrescentar uma subseção dentro da Etapa 4:

`### Criar regra geográfica — permitir somente Brasil`

Passo a passo pelo Console AWS atual:

1. Acessar:
   `WAF e Shield > Pacotes de proteção (ACLs da Web)`

2. Abrir:
   `waf-lab-xss`

3. Clicar em:
   `Gerenciar regras`

4. Clicar em:
   `Adicionar regra`

5. Selecionar:
   `Regra com base geográfica`

6. Em **Ação**, selecionar:
   `Block`

7. Nome:
   `Block-Fora-do-Brasil`

8. Em **Instrução**, selecionar:
   `País`

9. Selecionar:
   `Brasil / Brazil - BR`

10. Expandir:
    `Configuração de regras`

11. Em **Instrução de negação (NOT)**, marcar:
    `Negar resultados da instrução`

Explicar claramente:

- A condição identifica Brasil.
- O NOT inverte a condição.
- A ação é Block.
- Portanto:
  - Brasil → permitido.
  - Fora do Brasil → bloqueado.

Incluir um aviso destacado:

> Se `Negar resultados da instrução` NÃO estiver marcado, a regra fará o contrário e bloqueará os usuários do Brasil.

12. Em origem do IP, manter:
    `Endereço IP de origem`

Não selecionar endereço IP informado por cabeçalho para este laboratório.

---

# 3. DOCUMENTAR A RESPOSTA HTML PERSONALIZADA

Dentro da regra `Block-Fora-do-Brasil`, documentar:

Expandir:

`Resposta personalizada - opcional`

Marcar:

`Habilitar`

Código:

`403`

Cabeçalhos personalizados:

deixar vazio.

Criar novo corpo de resposta:

Nome padronizado:

`pagina_bloqueio_geo`

Tipo:

`HTML`

Não utilizar espaço, acento ou caracteres inválidos no nome.

Explicar que durante a implantação houve erro ao tentar utilizar um nome contendo espaços/acentos.

Informar também que o corpo HTML personalizado possui limite de tamanho mostrado pelo próprio Console AWS, atualmente limitado a aproximadamente `4 KB` para esse campo.

Depois de criar o corpo:

- voltar à regra;
- selecionar `pagina_bloqueio_geo`;
- manter código `403`;
- não configurar rótulos;
- clicar em `Adicionar regra`;
- salvar as alterações.

Remover da documentação qualquer referência conflitante ao nome `acesso-negado-br`.

Utilizar apenas:

`pagina_bloqueio_geo`

em todos os arquivos.

---

# 4. DOCUMENTAR A ORDEM E PRIORIDADE DAS REGRAS

Registrar a ordem atualmente utilizada:

1. `Block-XSS-Lab`
2. `Block-Fora-do-Brasil`

Explicar que regras com ação `Block` são terminativas.

Portanto, com essa prioridade:

- Brasil + requisição normal → permitido.
- Brasil + XSS → `Block-XSS-Lab`.
- Argentina + requisição normal → `Block-Fora-do-Brasil`.
- Argentina + XSS → pode ser bloqueada primeiro por `Block-XSS-Lab`, porque a regra XSS possui prioridade maior e a ação Block encerra a avaliação.

Corrigir qualquer trecho que diga simplesmente:

`Fora do Brasil + qualquer requisição = regra Block-Fora-do-Brasil`

porque isso não é necessariamente verdadeiro quando a requisição também contém XSS e `Block-XSS-Lab` vem primeiro.

---

# 5. CORRIGIR README.md

O README ainda descreve o projeto como tendo somente:

`1 Web ACL + 1 regra XSS`

Atualizar para:

`1 Web ACL + 2 regras`

Regras:

- `Block-XSS-Lab`
- `Block-Fora-do-Brasil`

Adicionar ao objetivo do laboratório que agora ele demonstra:

1. Detecção e bloqueio de XSS.
2. Restrição geográfica permitindo somente acessos originados do Brasil.
3. Resposta HTTP 403 personalizada para bloqueios geográficos.

Não transformar o projeto em um laboratório genérico de WAF. O foco principal continua sendo XSS, com geolocalização como proteção adicional.

---

# 6. CORRIGIR ARQUITETURA.md

Atualizar a arquitetura para representar duas regras dentro da Web ACL.

Fluxo COM WAF:

`Usuário`

`↓`

`Route 53`

`↓`

`CloudFront COM WAF`

`↓`

`AWS WAF - waf-lab-xss`

`↓`

`Block-XSS-Lab`

`↓`

`Block-Fora-do-Brasil`

`↓`

`S3 privado via OAC`

Explicar os três principais fluxos:

**Brasil + normal**

passa pelas duas regras → S3 → HTTP 200.

**Brasil + XSS**

`Block-XSS-Lab` → HTTP 403 → não chega ao S3.

**Fora do Brasil + normal**

passa pela regra XSS → `Block-Fora-do-Brasil` → HTTP 403 personalizado → não chega ao S3.

Atualizar também a tabela de componentes e a seção "Decisões de projeto", removendo a afirmação de que existe apenas uma regra.

---

# 7. CORRIGIR TESTE.md — WINDOWS

O teste no Windows funcionou corretamente utilizando PowerShell.

Tornar PowerShell o método recomendado para Windows.

Comando a partir da raiz:

```powershell
cd C:\github\WAF\aws-waf-lab-01-xss
```

Depois:

```powershell
.\tests\test-xss.ps1 -UrlSemWaf "https://site-sem-waf.dev.inhesta.net" -UrlComWaf "https://site-com-waf.dev.inhesta.net"
```

Se houver erro de Execution Policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Explicar que `Scope Process` altera somente a sessão atual.

Antes de executar, permitir opcionalmente validar:

```powershell
Test-Path .\tests\test-xss.ps1
```

Resultado esperado:

```text
SEM WAF
  Normal....................200
  XSS.......................200

COM WAF
  Normal....................200
  XSS.......................403 BLOCKED
```

---

# 8. CORRIGIR TESTE.md — PYTHON

Python deve permanecer como opção, mas NÃO deve ser tratado como requisito obrigatório para usuários Windows, porque o PowerShell já executa o teste sem dependências adicionais.

Antes de recomendar:

```powershell
python tests/test-xss.py
```

mandar validar:

```powershell
python --version
```

ou:

```powershell
py --version
```

Se nenhum deles existir, informar:

> Python não está disponível no PATH. No Windows, utilize o script PowerShell do laboratório ou instale/corrija o Python antes de utilizar a versão `.py`.

Não mandar o usuário continuar executando comandos Python se `python --version` falhar.

Não utilizar caminhos de instalação fictícios ou assumidos como:

`C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python312\python.exe`

sem antes confirmar que o arquivo realmente existe.

---

# 9. CORRIGIR O TESTE PELO SITE

Manter o recurso:

`Gerar URLs de teste`

Explicar claramente que a página:

- não executa ataques;
- não envia automaticamente as quatro requisições;
- apenas gera as URLs.

URLs geradas:

- SEM WAF normal.
- SEM WAF XSS.
- COM WAF normal.
- COM WAF XSS.

Explicar que:

`%3Cscript%3Ealert(1)%3C%2Fscript%3E`

é a representação URL encoded de:

`<script>alert(1)</script>`

e que a transformação `URL_DECODE` configurada na regra permite ao WAF analisar esse valor corretamente.

---

# 10. ADICIONAR TESTE GEOGRÁFICO

Adicionar ao `TESTE.md`:

`### Testar geolocalização`

**Teste Brasil**

- VPN desligada.
- Abrir:
  `https://site-com-waf.dev.inhesta.net`
- Esperado:
  `200`

**Teste fora do Brasil**

- Ativar VPN em outro país.
- Exemplo validado no laboratório: Argentina.
- Abrir novamente o mesmo endpoint.
- Esperado:
  `403`
- Deve aparecer a página HTML personalizada de acesso negado.

Abrir DevTools > Network e confirmar que o documento principal retorna:

`403`

Avisar para desligar a VPN antes dos testes específicos de XSS, para que a regra geográfica não interfira na interpretação do resultado.

---

# 11. CORRIGIR A VALIDAÇÃO NO PAINEL DO AWS WAF

A documentação atual utiliza nomenclaturas de interface que não correspondem exatamente ao Console AWS utilizado durante o teste.

Utilizar o fluxo atual:

`WAF e Shield`

`>`

`Pacotes de proteção (ACLs da Web)`

`>`

`waf-lab-xss`

`>`

`Visualizar painel, logs e solicitações de amostragem`

No painel:

- visualizar Total;
- Permitido;
- Bloqueado;
- atividade das regras;
- locais das solicitações;
- tipos de ataques.

Explicar que nenhuma configuração manual de dashboard no CloudWatch é necessária para esta validação. O próprio painel do WAF apresenta as métricas e possui links para o CloudWatch.

---

# 12. CORRIGIR SAMPLED REQUESTS

No Console atual, a área aparece como:

`Solicitações em amostra`

no próprio painel.

Não descrever obrigatoriamente como uma "aba Sampled requests".

Para validar XSS:

selecionar no campo `Metric name`:

`Block-XSS-Lab`

Esperado:

- Nome da métrica: `Block-XSS-Lab`
- IP de origem com `(BR)` no teste realizado no Brasil.
- URI semelhante a:
  `/?search=%3Cscript%3Ealert(1)...`
- Ação: `BLOCK`

Para validar geo:

selecionar:

`Block-Fora-do-Brasil`

Esperado no teste com VPN Argentina:

- Nome da métrica: `Block-Fora-do-Brasil`
- IP de origem mostrando `(AR)`.
- URI `/` ou `/favicon.ico`.
- Ação `BLOCK`.

Não exigir necessariamente uma coluna separada chamada `Country`, pois no Console utilizado o país apareceu ao lado do IP:

`(BR)`

ou:

`(AR)`.

---

# 13. CORRIGIR AS TABELAS DE RESULTADOS

Garantir Markdown válido, com três colunas:

| Origem | Requisição | Resultado |
|---|---|---|
| Brasil | Normal | 200 |
| Brasil | XSS | 403 — `Block-XSS-Lab` |
| Fora do Brasil | Normal | 403 — `Block-Fora-do-Brasil` + página personalizada |
| Fora do Brasil | XSS | 403 — primeira regra Block que corresponder segundo a prioridade |

Não deixar tabelas concatenadas como:

`OrigemRequisiçãoResultado`

---

# 14. CORRIGIR TROUBLESHOOTING

Adicionar os problemas efetivamente encontrados no laboratório:

**COM WAF + XSS retorna 200**

Verificar:

1. `Block-XSS-Lab` associada à Web ACL.
2. Ação `Block`.
3. `Todos os parâmetros de consulta`.
4. Tipo `Contém ataques de injeção de XSS`.
5. Transformação `Decodificar URL`.
6. Não deixar transformação como `Nenhum`.
7. Aguardar propagação.

**Brasil recebe página de bloqueio geográfico**

Verificar:

- país `Brazil - BR`;
- `Negar resultados da instrução` marcado.

**Fora do Brasil retorna 200**

Verificar:

- VPN realmente está saindo por outro país;
- regra `Block-Fora-do-Brasil`;
- ação Block;
- Source IP;
- propagação.

**Geo retorna 403 padrão em vez do HTML personalizado**

Verificar:

- resposta personalizada habilitada;
- código 403;
- corpo `pagina_bloqueio_geo` selecionado.

**`python` ou `py` não reconhecido**

Recomendar utilizar o script `.ps1` no Windows ou corrigir a instalação/PATH do Python.

**Script PowerShell não encontrado**

Confirmar se o terminal está na raiz do projeto.

Da raiz:

`.\tests\test-xss.ps1`

Se já estiver dentro de `tests`:

`.\test-xss.ps1`

---

# 15. CORRIGIR LINKS MARKDOWN

Remover qualquer URL interna do VS Code parecida com:

`https://file+.vscode-resource.vscode-cdn.net/...`

Substituir por links relativos portáveis:

`[IMPLANTACAO.md](IMPLANTACAO.md)`

`[TESTE.md](TESTE.md)`

`[ARQUITETURA.md](ARQUITETURA.md)`

---

# 16. CHECKLIST FINAL DA IMPLANTAÇÃO

Acrescentar ao final do `IMPLANTACAO.md` um checklist antes dos testes:

```text
[ ] Bucket S3 privado
[ ] OAC funcionando
[ ] CloudFront SEM WAF funcionando
[ ] CloudFront COM WAF funcionando
[ ] Certificado ACM emitido
[ ] Route 53 resolvendo os dois domínios
[ ] Web ACL waf-lab-xss associada somente ao endpoint COM WAF
[ ] Block-XSS-Lab = Block
[ ] Block-XSS-Lab inspeciona todos os parâmetros de consulta
[ ] Block-XSS-Lab usa URL_DECODE
[ ] Block-Fora-do-Brasil = Block
[ ] País = BR
[ ] NOT / Negate ativado
[ ] Source IP selecionado
[ ] pagina_bloqueio_geo selecionada
[ ] Resposta personalizada = 403
[ ] Ordem das regras conferida
[ ] Requisição normal COM WAF = 200
[ ] XSS COM WAF = 403
[ ] VPN Argentina = 403
[ ] Solicitação XSS visível em Solicitações em amostra
[ ] Solicitação AR visível em Solicitações em amostra
```

---

# REGRA IMPORTANTE PARA ESTA CORREÇÃO

Não inventar novos recursos AWS, não alterar a arquitetura para IaC e não transformar o laboratório em implantação automatizada.

Este projeto continua sendo implantado **manualmente pelo Console AWS**.

Atualize apenas a documentação e, caso algum script de teste precise de pequena correção para ficar consistente com a documentação, mostre exatamente qual alteração pretende fazer antes de modificar.

Depois das alterações, apresentar um resumo informando:

- quais arquivos foram alterados;
- quais inconsistências foram corrigidas;
- quais etapas novas foram adicionadas;
- e confirmar que README, ARQUITETURA, IMPLANTACAO e TESTE agora descrevem o mesmo ambiente.
