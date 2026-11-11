# Build Fira Code VN from the upstream fonts.
# Usage (PowerShell, from the repo root):  .\scripts\build.ps1
$ErrorActionPreference = 'Stop'
$root  = Split-Path $PSScriptRoot -Parent
$work  = Join-Path $root 'build'
$src   = Join-Path $work 'src'
$out   = Join-Path $root 'fonts\ttf'
New-Item -ItemType Directory -Force $work, $src, $out | Out-Null

# Run a native command; fail on non-zero exit code (not on stderr output,
# which Windows PowerShell 5.1 would otherwise treat as an error).
function Invoke-Native {
  $ErrorActionPreference = 'Continue'
  & $args[0] @($args | Select-Object -Skip 1) 2>&1 | ForEach-Object { "$_" }
  if ($LASTEXITCODE -ne 0) { throw "failed ($LASTEXITCODE): $($args -join ' ')" }
}

# 1. Python environment
$venv = Join-Path $work 'venv'
if (-not (Test-Path $venv)) { Invoke-Native python -m venv $venv }
$py = Join-Path $venv 'Scripts\python.exe'
Invoke-Native $py -m pip install -q --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')

# 2. Upstream fonts: Fira Code 6.2 + Fira Sans (Google Fonts)
$zip = Join-Path $src 'FiraCode.zip'
if (-not (Test-Path $zip)) {
  Invoke-WebRequest 'https://github.com/tonsky/FiraCode/releases/download/6.2/Fira_Code_v6.2.zip' -OutFile $zip
  Expand-Archive $zip (Join-Path $src 'FiraCode') -Force
}
foreach ($w in 'Light', 'Regular', 'Medium', 'SemiBold', 'Bold') {
  $f = Join-Path $src "FiraSans-$w.ttf"
  if (-not (Test-Path $f)) {
    Invoke-WebRequest "https://raw.githubusercontent.com/google/fonts/main/ofl/firasans/FiraSans-$w.ttf" -OutFile $f
  }
}

# 3. Build each weight, then re-hint with ttfautohint
$map = [ordered]@{ Light = 'Light'; Regular = 'Regular'; Retina = 'Regular'; Medium = 'Medium'; SemiBold = 'SemiBold'; Bold = 'Bold' }
foreach ($w in $map.Keys) {
  $raw = Join-Path $work "raw-$w.ttf"
  Invoke-Native $py -X utf8 (Join-Path $PSScriptRoot 'build_vn.py') `
      (Join-Path $src "FiraCode\ttf\FiraCode-$w.ttf") `
      (Join-Path $src "FiraSans-$($map[$w]).ttf") $raw
  Invoke-Native $py -m ttfautohint --no-info $raw (Join-Path $out "FiraCodeVN-$w.ttf")
}
Write-Host "Done -> $out"
