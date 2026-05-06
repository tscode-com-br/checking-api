param(
  [Parameter(Mandatory = $true)] [string]$ServerHost,
  [Parameter(Mandatory = $true)] [string]$User,
  [Parameter(Mandatory = $true)] [string]$KeyPath,
  [string]$RemoteDir = "~/checkcheck",
  [string]$ImageTag = $env:CHECKCHECK_DEPLOY_IMAGE_TAG,
  [string]$RegistryUsername = $env:GHCR_USERNAME,
  [string]$RegistryToken = $(if ($env:GHCR_TOKEN) { $env:GHCR_TOKEN } elseif ($env:GH_TOKEN) { $env:GH_TOKEN } else { $env:GITHUB_TOKEN })
)

$ErrorActionPreference = "Stop"

$defaultProdDirs = @("~/checkcheck", "/root/checkcheck")
$publicHealthUrl = if ($defaultProdDirs -contains $RemoteDir) { "https://tscode.com.br/api/health" } else { "" }

function ConvertTo-BashLiteral {
  param([Parameter(Mandatory = $true)][string]$Value)

  $singleQuote = [string][char]39
  $replacement = $singleQuote + '"' + $singleQuote + '"' + $singleQuote
  return $singleQuote + $Value.Replace($singleQuote, $replacement) + $singleQuote
}

function Resolve-GitCommitSha {
  $git = Get-Command git -ErrorAction SilentlyContinue
  if (-not $git) {
    return $null
  }

  $sha = (& $git.Source rev-parse HEAD 2>$null).Trim()
  if (-not $sha) {
    return $null
  }

  return $sha
}

function Test-GitWorkingTreeDirty {
  $git = Get-Command git -ErrorAction SilentlyContinue
  if (-not $git) {
    return $null
  }

  & $git.Source diff --quiet --ignore-submodules HEAD --
  return ($LASTEXITCODE -ne 0)
}

function Resolve-RegistryUsername {
  param([string]$ExplicitValue)

  foreach ($candidate in @($ExplicitValue, $env:GHCR_USERNAME, $env:GH_USERNAME, $env:GITHUB_ACTOR)) {
    if (-not [string]::IsNullOrWhiteSpace($candidate)) {
      return $candidate.Trim()
    }
  }

  $gh = Get-Command gh -ErrorAction SilentlyContinue
  if ($gh) {
    $login = (& $gh.Source api user --jq .login 2>$null).Trim()
    if ($login) {
      return $login
    }
  }

  throw "Nenhum usuario do GHCR foi encontrado. Defina GHCR_USERNAME/GITHUB_ACTOR ou autentique o GitHub CLI com gh auth login."
}

function Resolve-RegistryToken {
  param([string]$ExplicitValue)

  foreach ($candidate in @($ExplicitValue, $env:GHCR_TOKEN, $env:GH_TOKEN, $env:GITHUB_TOKEN)) {
    if (-not [string]::IsNullOrWhiteSpace($candidate)) {
      return $candidate.Trim()
    }
  }

  $gh = Get-Command gh -ErrorAction SilentlyContinue
  if ($gh) {
    $token = (& $gh.Source auth token 2>$null).Trim()
    if ($token) {
      return $token
    }
  }

  throw "Nenhum token do GHCR foi encontrado. Defina GHCR_TOKEN/GH_TOKEN/GITHUB_TOKEN ou autentique o GitHub CLI com gh auth login."
}

function Read-DotEnvMap {
  param([Parameter(Mandatory = $true)][string]$Path)

  $values = @{}
  foreach ($rawLine in Get-Content $Path) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#")) {
      continue
    }

    $separatorIndex = $line.IndexOf("=")
    if ($separatorIndex -lt 1) {
      continue
    }

    $name = $line.Substring(0, $separatorIndex).Trim()
    $value = $line.Substring($separatorIndex + 1).Trim()
    $values[$name] = $value
  }

  return $values
}

function Assert-TransportAiEnvGate {
  param([Parameter(Mandatory = $true)][hashtable]$EnvMap)

  $enabledValue = if ($EnvMap.ContainsKey("TRANSPORT_AI_ENABLED")) { $EnvMap["TRANSPORT_AI_ENABLED"] } else { "" }
  $normalizedEnabledValue = [string]$enabledValue
  if ($normalizedEnabledValue.Trim().ToLowerInvariant() -ne "true") {
    return
  }

  $approvalEvidence = if ($EnvMap.ContainsKey("TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE")) {
    [string]$EnvMap["TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE"]
  } else {
    ""
  }
  if ([string]::IsNullOrWhiteSpace($approvalEvidence)) {
    throw "TRANSPORT_AI_ENABLED=true exige TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE preenchido no .env antes do deploy."
  }

  $maxConcurrentRunsRaw = if ($EnvMap.ContainsKey("TRANSPORT_AI_MAX_CONCURRENT_RUNS")) {
    [string]$EnvMap["TRANSPORT_AI_MAX_CONCURRENT_RUNS"]
  } else {
    ""
  }
  $maxConcurrentRuns = 0
  if (-not [int]::TryParse($maxConcurrentRunsRaw, [ref]$maxConcurrentRuns) -or $maxConcurrentRuns -le 0) {
    throw "TRANSPORT_AI_ENABLED=true exige TRANSPORT_AI_MAX_CONCURRENT_RUNS inteiro e maior que zero no .env antes do deploy."
  }
}

function Assert-AppWorkersEnvGate {
  param([Parameter(Mandatory = $true)][hashtable]$EnvMap)

  $workersRaw = if ($EnvMap.ContainsKey("APP_WORKERS")) {
    [string]$EnvMap["APP_WORKERS"]
  } else {
    ""
  }

  $workers = 0
  if (-not [int]::TryParse($workersRaw, [ref]$workers) -or $workers -ne 1) {
    throw "APP_WORKERS=1 e obrigatorio no .env antes do deploy ate a validacao real de multiworker em tests/test_multiworker_realtime_postgres.py."
  }
}

if ([string]::IsNullOrWhiteSpace($ImageTag)) {
  $ImageTag = Resolve-GitCommitSha
  if (-not $ImageTag) {
    throw "Nao foi possivel resolver a imagem publicada do deploy manual. Defina CHECKCHECK_DEPLOY_IMAGE_TAG ou execute a partir de um clone Git valido."
  }

  $dirty = Test-GitWorkingTreeDirty
  if ($null -eq $dirty) {
    throw "Nao foi possivel validar o estado do working tree local. Defina CHECKCHECK_DEPLOY_IMAGE_TAG explicitamente para o redeploy manual."
  }
  if ($dirty) {
    throw "O deploy manual por imagem precompilada exige working tree limpo. Faca commit/push primeiro ou defina CHECKCHECK_DEPLOY_IMAGE_TAG para redeployar uma imagem ja publicada."
  }
}

$RegistryUsername = Resolve-RegistryUsername -ExplicitValue $RegistryUsername
$RegistryToken = Resolve-RegistryToken -ExplicitValue $RegistryToken
$AppImage = "ghcr.io/tscode-com-br/checkcheck-app:$ImageTag"
$quotedRemoteDir = ConvertTo-BashLiteral $RemoteDir

if (-not (Test-Path $KeyPath)) {
  throw "SSH key not found at: $KeyPath"
}

if (-not (Test-Path ".\\.env")) {
  throw "Missing .env in project root. Create it from deploy/.env.production.example before deploy."
}

$envMap = Read-DotEnvMap -Path ".\\.env"
Assert-TransportAiEnvGate -EnvMap $envMap
Assert-AppWorkersEnvGate -EnvMap $envMap

Write-Host "[1/4] Uploading project files..."
$tarCmd = "tar --exclude=.git --exclude=.venv --exclude=.pytest_cache --exclude=checking.db --exclude=test_checking.db -czf - ."
cmd /c $tarCmd | ssh -i $KeyPath "$User@$ServerHost" "mkdir -p $RemoteDir && tar -xzf - -C $RemoteDir"

Write-Host "[2/4] Uploading .env..."
scp -i $KeyPath .env "$User@$ServerHost`:$RemoteDir/.env"

Write-Host "[3/4] Starting containers..."
$quotedRegistryUsername = ConvertTo-BashLiteral $RegistryUsername
$quotedRegistryToken = ConvertTo-BashLiteral $RegistryToken
$quotedAppImage = ConvertTo-BashLiteral $AppImage
$remoteDeployLines = @(
  'set -euo pipefail',
  "cd $quotedRemoteDir",
  'TEMP_DOCKER_CONFIG="$(mktemp -d)"',
  'cleanup() {',
  '  rm -rf "$TEMP_DOCKER_CONFIG"',
  '}',
  'trap cleanup EXIT',
  'export DOCKER_CONFIG="$TEMP_DOCKER_CONFIG"',
  'docker compose up -d db',
  "printf '%s' $quotedRegistryToken | docker login ghcr.io -u $quotedRegistryUsername --password-stdin",
  "CHECKCHECK_APP_IMAGE=$quotedAppImage docker compose pull app",
  'docker logout ghcr.io || true',
  "export CHECKCHECK_APP_IMAGE=$quotedAppImage"
)
$rolloutCommand = "bash deploy/maintenance/run_app_rollout.sh --phase full --deploy-dir $quotedRemoteDir --release-id $(ConvertTo-BashLiteral $ImageTag)"
if (-not [string]::IsNullOrWhiteSpace($publicHealthUrl)) {
  $rolloutCommand += " --public-health-url $(ConvertTo-BashLiteral $publicHealthUrl)"
}
$remoteDeployLines += $rolloutCommand
$remoteDeployScript = [string]::Join("`n", $remoteDeployLines)
ssh -i $KeyPath "$User@$ServerHost" "bash -lc $(ConvertTo-BashLiteral $remoteDeployScript)"

Write-Host "[4/4] Local health check..."
ssh -i $KeyPath "$User@$ServerHost" "curl -fsS http://127.0.0.1:8000/api/health || true"

if (-not [string]::IsNullOrWhiteSpace($publicHealthUrl)) {
  Write-Host "[5/5] Public health check..."
  curl.exe -fsS $publicHealthUrl
}

Write-Host "Deploy completed."
