# CI-only prerequisite setup. Never called by GraphPaper or the user's launcher.
# Microsoft guidance: https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'This provisioning script is restricted to GitHub-hosted CI. It must not modify a user installation.'
}
$client = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
$keys = @("HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$client", "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$client", "HKCU:\Software\Microsoft\EdgeUpdate\Clients\$client")
function Get-WebViewVersion {
    foreach ($key in $keys) {
        $value = Get-ItemProperty -LiteralPath $key -Name pv -ErrorAction SilentlyContinue
        if ($value -and $value.pv -and $value.pv -ne '0.0.0.0') { return $value.pv }
    }
    return $null
}
$version = Get-WebViewVersion
Write-Host "CI WebView2 version before setup: $version"
Write-Host "CI interactive environment: $([Environment]::UserInteractive)"
if ($version) { Write-Host "WebView2 prerequisite is present: $version"; exit 0 }
$installer = Join-Path $env:RUNNER_TEMP 'MicrosoftEdgeWebview2Setup.exe'
Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $installer
$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
    throw 'The WebView2 bootstrapper did not have a valid Microsoft signature.'
}
$process = Start-Process -FilePath $installer -ArgumentList '/silent','/install' -PassThru
if (-not $process.WaitForExit(180000)) { throw 'The CI WebView2 installer exceeded its deadline.' }
Write-Host "Microsoft installer exit code: $($process.ExitCode)"
for ($attempt=0; $attempt -lt 60; $attempt++) {
    $version = Get-WebViewVersion
    if ($version) { break }
    Start-Sleep -Seconds 2
}
if (-not $version) { throw 'WebView2 is not available after CI prerequisite setup.' }
Write-Host "CI WebView2 ready: $version"
