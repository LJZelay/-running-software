$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourceRoot = Join-Path $PSScriptRoot "src\main\java"
$outputRoot = Join-Path $PSScriptRoot "out"

if (Test-Path $outputRoot) {
    Remove-Item -Path $outputRoot -Recurse -Force
}

New-Item -Path $outputRoot -ItemType Directory | Out-Null

$sources = Get-ChildItem -Path $sourceRoot -Recurse -Filter "*.java" |
    Select-Object -ExpandProperty FullName

if (-not $sources) {
    throw "No Java sources found under $sourceRoot"
}

& javac -encoding UTF-8 -d $outputRoot $sources
if ($LASTEXITCODE -ne 0) {
    throw "Java compilation failed"
}

& java -cp $outputRoot qa.QaTestRunner $repoRoot
if ($LASTEXITCODE -ne 0) {
    throw "Java integration QA reported failures"
}
