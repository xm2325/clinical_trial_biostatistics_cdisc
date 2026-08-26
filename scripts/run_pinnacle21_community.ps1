param(
    [Parameter(Mandatory=$true)][string]$ArtifactDir,
    [Parameter(Mandatory=$true)][string]$OutputDir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$communityVersion = '4.2.0'
$engineVersion = 'FDA 2508.1'
$adamVersion = '1.3'
$defineVersion = '2.1'
$installerUrl = 'https://dthfq9xldm1jq.cloudfront.net/site/Pinnacle%2021%20Community%20Setup%204.2.0.exe'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path
$ArtifactDir = (Resolve-Path $ArtifactDir).Path
$logPath = Join-Path $OutputDir 'pinnacle21_cli.log'
$installLog = Join-Path $OutputDir 'pinnacle21_package_inventory.txt'
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

# The Community 4.2.0 NSIS/Electron GUI installer crashes on the headless
# Windows Server 2025 runner. Extract the official package instead; the
# validation client and all P21 configuration files still come from that exact
# official installer. Java 8 is provided separately by actions/setup-java,
# matching P21's documented CLI runtime requirement.
$sevenZip = (Get-Command 7z.exe -ErrorAction SilentlyContinue).Source
if (-not $sevenZip) { $sevenZip = (Get-Command 7z -ErrorAction SilentlyContinue).Source }
if (-not $sevenZip) { throw '7-Zip is not available on the GitHub-hosted Windows runner.' }

$packageRoot = Join-Path $env:RUNNER_TEMP 'p21-community-4.2.0-extracted'
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
Write-Host "Extracting official Pinnacle 21 Community package with $sevenZip"
& $sevenZip x -y "-o$packageRoot" $installer | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "7-Zip could not extract the official Pinnacle 21 installer (exit $LASTEXITCODE)."
}

$nestedArchives = @(Get-ChildItem -Path $packageRoot -Recurse -File -Filter '*.7z' -ErrorAction SilentlyContinue)
foreach ($archive in $nestedArchives) {
    $nestedOut = Join-Path $archive.DirectoryName ($archive.BaseName + '_expanded')
    New-Item -ItemType Directory -Force -Path $nestedOut | Out-Null
    Write-Host "Expanding nested package payload $($archive.FullName)"
    & $sevenZip x -y "-o$nestedOut" $archive.FullName | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "7-Zip could not extract nested payload $($archive.Name) (exit $LASTEXITCODE)."
    }
}

$inventory = @(
    "PACKAGE_ROOT=$packageRoot"
    Get-ChildItem -Path $packageRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match 'p21-client.*\.jar$|ADaM-IG 1\.3 \(FDA\)\.xml$|Define-XML 2\.1 \(FDA\)\.xml$|Define\.xml \(FDA\)\.xml$' } |
        Select-Object -ExpandProperty FullName
)
$inventory | Set-Content -Encoding UTF8 $installLog

$jarCandidates = @(Get-ChildItem -Path $packageRoot -Recurse -File -Filter 'p21-client*.jar' -ErrorAction SilentlyContinue)
$jar = $jarCandidates | Sort-Object FullName | Select-Object -Last 1
if (-not $jar) {
    throw 'Pinnacle 21 Community CLI p21-client JAR was not found in the extracted official package.'
}

$targetConfig = Get-ChildItem -Path $packageRoot -Recurse -File -Filter 'ADaM-IG 1.3 (FDA).xml' -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\configs\\2508\.1\\' } |
    Select-Object -First 1
$defineConfig = Get-ChildItem -Path $packageRoot -Recurse -File -Filter 'Define-XML 2.1 (FDA).xml' -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\configs\\2508\.1\\' } |
    Select-Object -First 1
if (-not $targetConfig -or -not $defineConfig) {
    throw 'Expected FDA 2508.1 ADaM-IG 1.3 / Define-XML 2.1 configurations were not found in Community 4.2.0.'
}
$configsRoot = $targetConfig.Directory.Parent.FullName

if (-not $env:JAVA_HOME) { throw 'JAVA_HOME is not set; Pinnacle 21 Community CLI requires Java 8.' }
$java = Join-Path $env:JAVA_HOME 'bin\java.exe'
if (-not (Test-Path $java)) { throw "Java runtime not found at $java" }

$work = Join-Path $env:USERPROFILE 'Documents\Pinnacle 21 Community'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$cliJar = Join-Path $work $jar.Name
Copy-Item -Force $jar.FullName $cliJar
$workConfigs = Join-Path $work 'configs'
if (Test-Path $workConfigs) { Remove-Item -Recurse -Force $workConfigs }
Copy-Item -Recurse -Force $configsRoot $workConfigs

"community_version=$communityVersion`npackage_mode=EXTRACTED_OFFICIAL_INSTALLER`ncli_jar=$($jar.FullName)`njava_source=TEMURIN_JAVA_8`njava=$java`nengine=$engineVersion`nadam_ig=$adamVersion`ndefine_xml=$defineVersion`nconfig_root=$configsRoot`ndefine=$($define.FullName)" |
    Set-Content -Encoding UTF8 (Join-Path $OutputDir 'pinnacle21_runtime_identity.txt')

Push-Location $work
try {
    Write-Host "CLI: $cliJar"
    Write-Host "Java: $java"
    & $java -version 2>&1 | Tee-Object -FilePath $logPath
    $javaVersionOutput = (& $java -version 2>&1 | Out-String)
    if ($javaVersionOutput -notmatch 'version "1\.8\.') {
        throw "Pinnacle 21 Community CLI requires Java 8; observed: $javaVersionOutput"
    }
    & $java -jar $cliJar --help 2>&1 | Tee-Object -FilePath $logPath -Append

    $args = @(
        '-jar', $cliJar,
        "--engine.version=$engineVersion",
        '--standard=adam',
        "--standard.version=$adamVersion",
        "--source.define.standard=$defineVersion",
        "--source.define=$($define.FullName)",
        "--report=$reportPath"
    )
    Write-Host ('Executing Pinnacle 21 Community CLI: java ' + ($args -join ' '))
    & $java @args 2>&1 | Tee-Object -FilePath $logPath -Append
    $cliExit = $LASTEXITCODE
    "cli_exit_code=$cliExit" | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'pinnacle21_cli_exit_code.txt')
}
finally {
    Pop-Location
}

if (-not (Test-Path $reportPath)) {
    Write-Host 'Pinnacle 21 report was not produced. CLI log tail:'
    if (Test-Path $logPath) { Get-Content $logPath -Tail 200 }
    throw "Pinnacle 21 Community execution did not create $reportPath"
}

Write-Host "Pinnacle 21 Community report created: $reportPath"
python scripts/review_pinnacle21_report.py --report "$reportPath" --log "$logPath" --output-dir "$OutputDir" --community-version "$communityVersion"
