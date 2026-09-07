<#
.SYNOPSIS
    Script de teste da API do AWS WAF Security Lab 03 (SQL Injection).

.DESCRIPTION
    Reproduz em PowerShell o mesmo contrato do script Python tests/test-sqli.py.
    Valida o comportamento da API nos ambientes sem WAF (sem-waf) e com WAF (com-waf),
    incluindo a requisicao de SQL Injection de teste usada apenas para acionar a
    inspecao do WAF (sem vulnerabilidade real).

    Uso responsavel: o script envia um numero reduzido de requisicoes, direcionadas
    somente aos endpoints do laboratorio, sem loops continuos, sem stress, sem flood
    e sem DDoS (Requisito 21).

.PARAMETER BaseUrl
    URL base do endpoint alvo (ex.: https://api-sem-waf.exemplo.com).
    Parametro obrigatorio.

.PARAMETER Environment
    Identificador de ambiente: 'sem-waf' ou 'com-waf'.
    Parametro obrigatorio.

.EXAMPLE
    ./test-sqli.ps1 -BaseUrl https://api-sem-waf.exemplo.com -Environment sem-waf

.EXAMPLE
    ./test-sqli.ps1 -BaseUrl https://api-com-waf.exemplo.com -Environment com-waf

.NOTES
    Codigo de saida 0 quando todos os testes forem aprovados; diferente de 0 quando
    ao menos um teste for reprovado (Requisito 20.11).
#>

[CmdletBinding()]
param(
    # URL base do endpoint alvo (obrigatorio) - Requisito 20.2
    [Parameter(Mandatory = $false)]
    [string]$BaseUrl,

    # Identificador de ambiente: sem-waf ou com-waf (obrigatorio) - Requisito 20.2
    [Parameter(Mandatory = $false)]
    [ValidateSet('sem-waf', 'com-waf')]
    [string]$Environment
)

# Timeout de 30 segundos por requisicao (Requisito 20.8)
$script:RequestTimeoutSec = 30

# Requisicao de SQL Injection de teste (Requisito 3.4 / 15.5 / 15.6)
# Usada apenas para acionar a inspecao do WAF; nao ha vulnerabilidade real.
$script:SqlInjectionQuery = "id=1' OR '1'='1"

# --------------------------------------------------------------------------
# Funcao: Test-RequiredParameters
# Valida os parametros obrigatorios. Se algum faltar, exibe mensagem indicando
# o que esta ausente e retorna a lista de parametros faltantes (Requisito 20.3).
# --------------------------------------------------------------------------
function Test-RequiredParameters {
    param(
        [string]$BaseUrl,
        [string]$Environment
    )

    $missing = @()

    if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
        $missing += 'BaseUrl (URL base do endpoint alvo)'
    }

    if ([string]::IsNullOrWhiteSpace($Environment)) {
        $missing += 'Environment (identificador de ambiente: sem-waf ou com-waf)'
    }

    return $missing
}

# --------------------------------------------------------------------------
# Funcao: Get-NormalizedBaseUrl
# Remove barras finais para evitar barras duplicadas ao montar as URLs.
# --------------------------------------------------------------------------
function Get-NormalizedBaseUrl {
    param([string]$BaseUrl)
    return $BaseUrl.TrimEnd('/')
}

# --------------------------------------------------------------------------
# Funcao: Invoke-LabRequest
# Executa uma requisicao GET com timeout de 30s e captura o codigo HTTP mesmo
# em respostas de erro (ex.: 403 e 404). Em PowerShell, codigos 4xx/5xx podem
# lancar excecao; o status e recuperado via $_.Exception.Response (Requisito 20.8).
#
# Retorna um objeto com:
#   StatusCode : codigo HTTP recebido (ou $null em falha de conexao/timeout)
#   Error      : mensagem de erro (ou $null)
# --------------------------------------------------------------------------
function Invoke-LabRequest {
    param(
        [string]$Url
    )

    $result = [PSCustomObject]@{
        StatusCode = $null
        Error      = $null
    }

    try {
        # -UseBasicParsing garante compatibilidade; -TimeoutSec aplica o limite de 30s.
        $response = Invoke-WebRequest -Uri $Url -Method Get `
            -TimeoutSec $script:RequestTimeoutSec -UseBasicParsing -ErrorAction Stop
        $result.StatusCode = [int]$response.StatusCode
    }
    catch [System.Net.WebException] {
        # Tenta extrair o status HTTP da resposta de erro (ex.: 403 do WAF, 404 da Lambda).
        $webResponse = $_.Exception.Response
        if ($null -ne $webResponse -and $null -ne $webResponse.StatusCode) {
            $result.StatusCode = [int]$webResponse.StatusCode
        }
        else {
            # Falha de conexao ou timeout: sem status HTTP.
            $result.Error = $_.Exception.Message
        }
    }
    catch {
        # PowerShell Core (7+) lanca Microsoft.PowerShell.Commands.HttpResponseException,
        # que expone o status via a propriedade Response.
        $httpResponse = $_.Exception.Response
        if ($null -ne $httpResponse -and $null -ne $httpResponse.StatusCode) {
            $result.StatusCode = [int]$httpResponse.StatusCode
        }
        elseif ($null -ne $_.Exception.Response.StatusCode.value__) {
            $result.StatusCode = [int]$_.Exception.Response.StatusCode.value__
        }
        else {
            $result.Error = $_.Exception.Message
        }
    }

    return $result
}

# --------------------------------------------------------------------------
# Funcao: Write-TestResult
# Apresenta o resultado de uma requisicao de forma padronizada (Requisito 20.10):
# endpoint testado, codigo HTTP recebido, codigo HTTP esperado e veredito.
# Retorna $true se aprovado e $false se reprovado.
# --------------------------------------------------------------------------
function Write-TestResult {
    param(
        [string]$Endpoint,
        [int]$Expected,
        $Requested   # objeto retornado por Invoke-LabRequest
    )

    $received = $Requested.StatusCode
    $passed = ($null -ne $received) -and ($received -eq $Expected)

    $receivedText = if ($null -ne $received) { "$received" } else { 'falha de conexao/timeout' }
    $verdict = if ($passed) { 'APROVADO' } else { 'REPROVADO' }

    Write-Host "  Endpoint       : $Endpoint"
    Write-Host "  HTTP recebido  : $receivedText"
    Write-Host "  HTTP esperado  : $Expected"
    Write-Host "  Veredito       : $verdict"

    # Em caso de falha de conexao/timeout, exibe o endpoint e a causa (Requisito 20.8).
    if ($null -eq $received -and $null -ne $Requested.Error) {
        Write-Host "  Causa da falha : $($Requested.Error)"
    }

    Write-Host ''
    return $passed
}

# --------------------------------------------------------------------------
# Funcao: Invoke-EnvironmentTests
# Executa o conjunto de testes de um ambiente e retorna $true se todos
# aprovados, $false caso contrario.
#
# sem-waf : /health -> 200, /produto -> 200, SQLi de teste -> 200
# com-waf : /health -> 200, /produto -> 200, SQLi de teste -> 403 (origem Brasil)
# (Requisitos 20.4, 20.5, 20.6, 20.7)
# --------------------------------------------------------------------------
function Invoke-EnvironmentTests {
    param(
        [string]$BaseUrl,
        [string]$Environment
    )

    # Codigo HTTP esperado para a SQL Injection de teste depende do ambiente.
    $sqliExpected = if ($Environment -eq 'com-waf') { 403 } else { 200 }

    # Conjunto reduzido e fixo de requisicoes (uso responsavel - Requisito 21).
    $checks = @(
        @{ Endpoint = "$BaseUrl/health"; Expected = 200 },
        @{ Endpoint = "$BaseUrl/produto"; Expected = 200 },
        @{ Endpoint = "$BaseUrl/produto?$script:SqlInjectionQuery"; Expected = $sqliExpected }
    )

    $allPassed = $true

    foreach ($check in $checks) {
        $requested = Invoke-LabRequest -Url $check.Endpoint
        $passed = Write-TestResult -Endpoint $check.Endpoint -Expected $check.Expected -Requested $requested
        if (-not $passed) {
            $allPassed = $false
        }
    }

    return $allPassed
}

# ==========================================================================
# Execucao principal
# ==========================================================================

# Validacao de parametros obrigatorios (Requisito 20.3).
$missingParams = Test-RequiredParameters -BaseUrl $BaseUrl -Environment $Environment

if ($missingParams.Count -gt 0) {
    Write-Host 'ERRO: parametros obrigatorios ausentes.' -ForegroundColor Red
    foreach ($param in $missingParams) {
        Write-Host "  - $param"
    }
    Write-Host ''
    Write-Host 'Uso:'
    Write-Host '  ./test-sqli.ps1 -BaseUrl <url-base> -Environment <sem-waf|com-waf>'
    # Encerra sem executar requisicoes e com codigo de saida diferente de 0.
    exit 2
}

$normalizedBaseUrl = Get-NormalizedBaseUrl -BaseUrl $BaseUrl

Write-Host '=========================================================='
Write-Host ' AWS WAF Security Lab 03 - Teste de API (SQL Injection)'
Write-Host '=========================================================='
Write-Host " Ambiente alvo : $Environment"
Write-Host " URL base      : $normalizedBaseUrl"
Write-Host '=========================================================='
Write-Host ''

# --------------------------------------------------------------------------
# Bloco geografico: origem no Brasil (Requisito 20.9)
# Este bloco executa contra o ambiente informado, presumindo origem no Brasil.
# --------------------------------------------------------------------------
Write-Host '----------------------------------------------------------'
Write-Host ' BLOCO 1 - Origem no Brasil'
Write-Host '----------------------------------------------------------'
Write-Host ''

$brasilPassed = Invoke-EnvironmentTests -BaseUrl $normalizedBaseUrl -Environment $Environment

# --------------------------------------------------------------------------
# Bloco geografico: origem fora do Brasil (Requisito 20.9)
# Este bloco documenta o comportamento esperado quando a requisicao parte de
# fora do Brasil. A origem geografica e determinada pela AWS a partir do IP de
# origem; nao e possivel forjar a origem apenas com este script. Por isso, o
# resultado deste bloco e informativo e depende do local real de execucao.
# --------------------------------------------------------------------------
Write-Host '----------------------------------------------------------'
Write-Host ' BLOCO 2 - Origem fora do Brasil'
Write-Host '----------------------------------------------------------'
Write-Host ''

if ($Environment -eq 'com-waf') {
    Write-Host ' Observacao: no ambiente com-waf, requisicoes com origem fora do'
    Write-Host ' Brasil sao bloqueadas pela regra Block-Fora-do-Brasil (HTTP 403).'
    Write-Host ' Execute este script a partir de uma origem fora do Brasil (por'
    Write-Host ' exemplo, uma VPN ou host em outra regiao) para observar o 403.'
}
else {
    Write-Host ' Observacao: no ambiente sem-waf nao ha bloqueio geografico; o'
    Write-Host ' comportamento e o mesmo independentemente da origem.'
}
Write-Host ''

# Executa o mesmo conjunto de requisicoes, identificando o bloco de origem.
# Nota: o veredito real depende da origem geografica efetiva da execucao.
$foraBrasilPassed = Invoke-EnvironmentTests -BaseUrl $normalizedBaseUrl -Environment $Environment

# --------------------------------------------------------------------------
# Agregacao do veredito e codigo de saida (Requisito 20.11)
# --------------------------------------------------------------------------
Write-Host '=========================================================='
Write-Host ' RESUMO'
Write-Host '=========================================================='
Write-Host " Bloco 1 (Origem no Brasil)      : $(if ($brasilPassed) { 'APROVADO' } else { 'REPROVADO' })"
Write-Host " Bloco 2 (Origem fora do Brasil) : $(if ($foraBrasilPassed) { 'APROVADO' } else { 'REPROVADO' })"
Write-Host '=========================================================='

if ($brasilPassed -and $foraBrasilPassed) {
    Write-Host 'Todos os testes foram aprovados.' -ForegroundColor Green
    exit 0
}
else {
    Write-Host 'Ao menos um teste foi reprovado.' -ForegroundColor Red
    exit 1
}
