param(
    [Parameter(Mandatory=$true)][string]$ArtifactDir,
    [Parameter(Mandatory=$true)][string]$OutputDir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$communityVersion = '4.2.0'
$installerUrl = 'https://dthfq9xldm1jq.cloudfront.net/site/Pinnacle%2021%20Community%20Setup%204.2.0.exe'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path
$ArtifactDir = (Resolve-Path $ArtifactDir).Path
$logPath = Join-Path $OutputDir 'pinnacle21_cli.log'
$installLog = Join-Path $OutputDir 'pinnacle21_install_inventory.txt'
$reportPath = Join-Path $OutputDir 'pinnacle21_define_report.xlsx'

$define = Get-ChildItem -Path $ArtifactDir -Recurse -File -Filter 'define_xml_candidate_v0_26.xml' | Select-Object -First 1
if (-not $define) {
    throw "define_xml_candidate_v0_26.xml not found under $ArtifactDir"
}

$installer = Join-Path $env:RUNNER_TEMP 'Pinnacle21CommunitySetup-4.2.0.exe'
Write-Host "Downloading official Pinnacle 21 Community $communityVersion installer"
Invoke-WebRequest -Uri $installerUrl -OutFile $installer
$installerHash = (Get-FileHash -Algorithm SHA256 -Path $installer).Hash.ToLowerInvariant()
"version=$communityVersion`nurl=$installerUrl`nsha256=$installerHash" | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'pinnacle21_installer_identity.txt')

Write-Host 'Installing Pinnacle 21 Community silently on ephemeral Windows runner'
$process = Start-Process -FilePath $installer -ArgumentList '/S' -Wait -PassThru
if ($process.ExitCode -ne 0) {
    throw "Pinnacle 21 Community installer exit code: $($process.ExitCode)"
}

$roots = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Pinnacle 21 Community'),
    (Join-Path $env:LOCALAPPDATA 'Programs\pinnacle21-community'),
    (Join-Path ${env:ProgramFiles(x86)} 'Pinnacle 21 Community'),
    (Join-Path $env:ProgramFiles 'Pinnacle 21 Community')
) | Where-Object { $_ -and (Test-Path $_) }

if (-not $roots) {
    throw 'Pinnacle 21 Community installation directory was not found after silent install.'
}

$inventory = foreach ($root in $roots) {
    "ROOT=$root"
    Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match 'p21-client.*\.jar$|java\.exe$|\.xml$' } |
        Select-Object -ExpandProperty FullName
}
$inventory | Set-Content -Encoding UTF8 $installLog

$jar = foreach ($root in $roots) {
    Get-ChildItem -Path $root -Recurse -File -Filter 'p21-client*.jar' -ErrorAction SilentlyContinue
} | Sort-Object FullName | Select-Object -Last 1
if (-not $jar) {
    throw 'Pinnacle 21 Community CLI p21-client JAR was not found after install.'
}

$java = foreach ($root in $roots) {
    Get-ChildItem -Path $root -Recurse -File -Filter 'java.exe' -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match 'components\\java64\\bin\\java\.exe$' }
} | Select-Object -First 1
if (-not $java) {
    throw 'Bundled Pinnacle 21 Java 8 runtime was not found.'
}

$work = Join-Path $env:USERPROFILE 'Documents\Pinnacle 21 Community'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$cliJar = Join-Path $work $jar.Name
Copy-Item -Force $jar.FullName $cliJar

"community_version=$communityVersion`ncli_jar=$($jar.FullName)`njava=$($java.FullName)`ndefine=$($define.FullName)" |
    Set-Content -Encoding UTF8 (Join-Path $OutputDir 'pinnacle21_runtime_identity.txt')

Push-Location $work
try {
    Write-Host "CLI: $cliJar"
    Write-Host "Java: $($java.FullName)"
    & $java.FullName -version 2>&1 | Tee-Object -FilePath $logPath
    & $java.FullName -jar $cliJar --help 2>&1 | Tee-Object -FilePath $logPath -Append

    $args = @(
        '-jar', $cliJar,
        '--engine.version=FDA 2304.3',
        '--standard=adam',
        '--standard.version=1.2',
        '--define.standard=2.1',
        "--source.define=$($define.FullName)",
        "--report=$reportPath"
    )
    Write-Host ('Executing Pinnacle 21 Community CLI: java ' + ($args -join ' '))
    & $java.FullName @args 2>&1 | Tee-Object -FilePath $logPath -Append
    $cliExit = $LASTEXITCODE
    "cli_exit_code=$cliExit" | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'pinnacle21_cli_exit_code.txt')
}
finally {
    Pop-Location
}

if (-not (Test-Path $reportPath)) {
    Write-Host 'Pinnacle 21 report was not produced. CLI log tail:'
    Get-Content $logPath -Tail 160
    throw "Pinnacle 21 Community execution did not create $reportPath"
}

Write-Host "Pinnacle 21 Community report created: $reportPath"
python scripts/review_pinnacle21_report.py --report "$reportPath" --log "$logPath" --output-dir "$OutputDir" --community-version "$communityVersion"
