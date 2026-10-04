param(
    [switch]$NoSend
)

$ErrorActionPreference = "Stop"

$projectDirectory = $PSScriptRoot
$pythonPath = Join-Path $projectDirectory ".venv\Scripts\python.exe"
$mainPath = Join-Path $projectDirectory "main.py"
$logDirectory = Join-Path $projectDirectory "logs"
$logPath = Join-Path $logDirectory "daily-run.log"

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
Set-Location -LiteralPath $projectDirectory

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"$timestamp | INFO | 예약 실행 시작" | Out-File -FilePath $logPath -Append -Encoding utf8

$pythonArguments = @($mainPath)
if (-not $NoSend) {
    $pythonArguments += "--send"
}

# Windows PowerShell treats a native program's stderr output as an ErrorRecord.
# Python logging writes INFO messages to stderr, so temporarily use Continue and
# merge both streams into the log. The process exit code remains authoritative.
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $pythonPath @pythonArguments 2>&1 |
    ForEach-Object { $_.ToString() } |
    Out-File -FilePath $logPath -Append -Encoding utf8
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if ($exitCode -eq 0) {
    "$timestamp | INFO | 예약 실행 완료" | Out-File -FilePath $logPath -Append -Encoding utf8
} else {
    "$timestamp | ERROR | 예약 실행 실패 (종료 코드: $exitCode)" | Out-File -FilePath $logPath -Append -Encoding utf8
}

exit $exitCode
