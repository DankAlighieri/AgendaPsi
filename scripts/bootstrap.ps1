<#
.SYNOPSIS
Prepara o ambiente local do AgendaPsi no Windows.

.DESCRIPTION
Cria o ambiente virtual em .venv, instala o requirements.txt e aplica as
migracoes. Pode ser executado mais de uma vez. O bootstrap.sh continua sendo
o script usado pelo Vagrant.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $raiz '.venv\Scripts\python.exe'

function Test-Python {
    param([string]$Comando, [string[]]$Argumentos = @())

    # Um interpretador ausente ou antigo nao deve interromper a busca.
    $ErrorActionPreference = 'Continue'
    if (-not (Get-Command $Comando -ErrorAction SilentlyContinue)) {
        return $false
    }
    $codigo = 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'
    & $Comando @Argumentos -c $codigo 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Invoke-Passo {
    param([string]$Descricao, [string]$Comando, [string[]]$Argumentos)

    # O sucesso e decidido pelo codigo de saida, nao por avisos no stderr.
    $ErrorActionPreference = 'Continue'
    Write-Host "==> $Descricao"
    & $Comando @Argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "Falha na etapa '$Descricao' (codigo $LASTEXITCODE)."
    }
}

# Impede que o gerenciador do Python baixe uma versao sem ser pedido.
$instalacaoAutomatica = $env:PYTHON_MANAGER_AUTOMATIC_INSTALL
$env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'
Push-Location $raiz

try {
    if (-not (Test-Path $venvPython)) {
        $candidatos = @(
            @{ Comando = 'py'; Argumentos = @('-3') },
            @{ Comando = 'python'; Argumentos = @() },
            @{ Comando = 'python3'; Argumentos = @() }
        )
        $python = $null
        foreach ($candidato in $candidatos) {
            if (Test-Python $candidato.Comando $candidato.Argumentos) {
                $python = $candidato
                break
            }
        }
        if (-not $python) {
            throw 'Python 3.12 ou superior nao encontrado. Instale em https://www.python.org/downloads/ e execute de novo.'
        }
        Invoke-Passo 'Criando o ambiente virtual (.venv)' $python.Comando ($python.Argumentos + @('-m', 'venv', '.venv'))
    }
    elseif (-not (Test-Python $venvPython)) {
        throw 'O ambiente .venv esta quebrado ou usa um Python anterior ao 3.12. Apague a pasta .venv e execute de novo.'
    }

    Invoke-Passo 'Instalando as dependencias' $venvPython @('-m', 'pip', 'install', '-r', 'requirements.txt')
    Invoke-Passo 'Aplicando as migracoes' $venvPython @('manage.py', 'migrate')

    Write-Host ''
    Write-Host 'Ambiente pronto. Para iniciar o servidor, na pasta do projeto:'
    Write-Host '    .\.venv\Scripts\python.exe manage.py runserver'
}
finally {
    Pop-Location
    $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = $instalacaoAutomatica
}
