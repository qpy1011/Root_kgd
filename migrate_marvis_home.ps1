$ErrorActionPreference = 'Stop'

$source = 'C:\Users\Administrator\AppData\Roaming\Tencent\Marvis'
$target = 'E:\Marvis\MarvisHome'
$parent = Split-Path -Parent $source
$backup = Join-Path $parent ('Marvis.backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
$log = 'E:\model\Root_kgd\marvis_migration_admin.log'

function Write-Log {
    param([string]$Message)
    $line = ('{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
    Add-Content -LiteralPath $log -Value $line
    Write-Host $line
}

Write-Log 'Starting Marvis home migration finalization.'

Write-Log 'Looking for Marvis-related processes.'
$currentPid = $PID
$processes = @()
try {
    $processes = Get-CimInstance Win32_Process -ErrorAction Stop |
        Where-Object {
            $_.ProcessId -ne $currentPid -and (
                $_.Name -like 'Marvis*' -or
                $_.ExecutablePath -like 'E:\Marvis\*' -or
                $_.CommandLine -like '*E:\Marvis\*' -or
                $_.CommandLine -like '*C:\Users\Administrator\AppData\Roaming\Tencent\Marvis*'
            )
        }
} catch {
    Write-Log "Process command-line query failed: $($_.Exception.Message)"
}

foreach ($proc in $processes) {
    Write-Log "Stopping process: $($proc.Name) PID=$($proc.ProcessId)"
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Id -ne $currentPid -and $_.ProcessName -like 'Marvis*' } |
    ForEach-Object {
        Write-Log "Stopping process by name: $($_.ProcessName) PID=$($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2

if (-not (Test-Path -LiteralPath $target)) {
    throw "Target path does not exist: $target"
}

if (-not (Test-Path -LiteralPath $source)) {
    throw "Source path does not exist: $source"
}

$sourceItem = Get-Item -LiteralPath $source -Force
if ($sourceItem.LinkType -eq 'Junction') {
    Write-Log "Source is already a junction: $source -> $($sourceItem.Target -join ', ')"
    exit 0
}

Write-Log 'Synchronizing latest source data to target.'
& robocopy $source $target /E /COPY:DAT /DCOPY:DAT /XJ /R:2 /W:1 /NFL /NDL /NP | ForEach-Object {
    Write-Log $_
}
$robocopyExit = $LASTEXITCODE
if ($robocopyExit -ge 8) {
    throw "Robocopy failed with exit code $robocopyExit"
}

$nestedJunction = 'User\oAN1i2Rlhu1An2zA6TIc8GKr7mD4\workspace'
$targetNestedJunction = Join-Path $target $nestedJunction
if (-not (Test-Path -LiteralPath $targetNestedJunction)) {
    $targetNestedParent = Split-Path -Parent $targetNestedJunction
    if (-not (Test-Path -LiteralPath $targetNestedParent)) {
        New-Item -ItemType Directory -Path $targetNestedParent | Out-Null
    }
    Write-Log "Recreating nested workspace junction: $targetNestedJunction -> E:\Marvis\workspace"
    New-Item -ItemType Junction -Path $targetNestedJunction -Target 'E:\Marvis\workspace' | Out-Null
}

function New-RootJunction {
    Write-Log "Renaming original source to backup: $backup"
    Rename-Item -LiteralPath $source -NewName (Split-Path -Leaf $backup)
    Write-Log "Creating junction: $source -> $target"
    New-Item -ItemType Junction -Path $source -Target $target | Out-Null
}

function Restore-RootBackup {
    if (Test-Path -LiteralPath $source) {
        Remove-Item -LiteralPath $source -Force
    }
    Rename-Item -LiteralPath $backup -NewName 'Marvis'
}

function New-ChildJunctions {
    Write-Log 'Falling back to child directory junctions.'
    foreach ($name in @('cef', 'db', 'marvis-offline-page', 'User')) {
        $sourceChild = Join-Path $source $name
        $targetChild = Join-Path $target $name
        $backupChild = Join-Path $source ($name + '.backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
        if (-not (Test-Path -LiteralPath $sourceChild)) {
            Write-Log "Skipping missing source child: $sourceChild"
            continue
        }
        $childItem = Get-Item -LiteralPath $sourceChild -Force
        if ($childItem.LinkType -eq 'Junction') {
            Write-Log "Child already junction: $sourceChild -> $($childItem.Target -join ', ')"
            continue
        }
        if (-not (Test-Path -LiteralPath $targetChild)) {
            throw "Target child missing: $targetChild"
        }
        try {
            Write-Log "Renaming child to backup: $sourceChild -> $backupChild"
            Rename-Item -LiteralPath $sourceChild -NewName (Split-Path -Leaf $backupChild)
            Write-Log "Creating child junction: $sourceChild -> $targetChild"
            New-Item -ItemType Junction -Path $sourceChild -Target $targetChild | Out-Null
        } catch {
            Write-Log "Child junction failed for ${name}: $($_.Exception.Message)"
            if ($name -eq 'User') {
                New-UserAccountJunctions
            } else {
                throw
            }
        }
    }
}

function New-UserAccountJunctions {
    Write-Log 'Falling back to per-account junctions under User.'
    $sourceUser = Join-Path $source 'User'
    $targetUser = Join-Path $target 'User'
    foreach ($account in Get-ChildItem -LiteralPath $sourceUser -Directory -Force) {
        $sourceAccount = $account.FullName
        $targetAccount = Join-Path $targetUser $account.Name
        $backupAccount = Join-Path $sourceUser ($account.Name + '.backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
        $accountItem = Get-Item -LiteralPath $sourceAccount -Force
        if ($accountItem.LinkType -eq 'Junction') {
            Write-Log "Account already junction: $sourceAccount -> $($accountItem.Target -join ', ')"
            continue
        }
        if (-not (Test-Path -LiteralPath $targetAccount)) {
            throw "Target account missing: $targetAccount"
        }
        try {
            Write-Log "Renaming account to backup: $sourceAccount -> $backupAccount"
            Rename-Item -LiteralPath $sourceAccount -NewName (Split-Path -Leaf $backupAccount)
            Write-Log "Creating account junction: $sourceAccount -> $targetAccount"
            New-Item -ItemType Junction -Path $sourceAccount -Target $targetAccount | Out-Null
        } catch {
            Write-Log "Account junction failed for $($account.Name): $($_.Exception.Message)"
            New-UserAccountChildJunctions -AccountName $account.Name
        }
    }
}

function New-UserAccountChildJunctions {
    param([string]$AccountName)
    Write-Log "Falling back to child junctions for account: $AccountName"
    $sourceAccount = Join-Path (Join-Path $source 'User') $AccountName
    $targetAccount = Join-Path (Join-Path $target 'User') $AccountName
    foreach ($child in Get-ChildItem -LiteralPath $sourceAccount -Directory -Force) {
        $sourceAccountChild = $child.FullName
        $targetAccountChild = Join-Path $targetAccount $child.Name
        $backupAccountChild = Join-Path $sourceAccount ($child.Name + '.backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
        $childItem = Get-Item -LiteralPath $sourceAccountChild -Force
        if ($childItem.LinkType -eq 'Junction') {
            Write-Log "Account child already junction: $sourceAccountChild -> $($childItem.Target -join ', ')"
            continue
        }
        if (-not (Test-Path -LiteralPath $targetAccountChild)) {
            Write-Log "Skipping missing target account child: $targetAccountChild"
            continue
        }
        Write-Log "Renaming account child to backup: $sourceAccountChild -> $backupAccountChild"
        Rename-Item -LiteralPath $sourceAccountChild -NewName (Split-Path -Leaf $backupAccountChild)
        Write-Log "Creating account child junction: $sourceAccountChild -> $targetAccountChild"
        New-Item -ItemType Junction -Path $sourceAccountChild -Target $targetAccountChild | Out-Null
    }
}

$usedFallback = $false
try {
    New-RootJunction
} catch {
    Write-Log "Root junction failed: $($_.Exception.Message)"
    if (Test-Path -LiteralPath $backup) {
        Write-Log 'Attempting to restore root backup after failed root junction.'
        Restore-RootBackup
    }
    New-ChildJunctions
    $usedFallback = $true
}

try {
    $verify = Get-Item -LiteralPath $source -Force
    Write-Log "Verified source LinkType: $($verify.LinkType)"
    Write-Log "Verified source Target: $($verify.Target -join ', ')"
    foreach ($name in @('cef', 'db', 'marvis-offline-page', 'User')) {
        $sourceChild = Join-Path $source $name
        if (Test-Path -LiteralPath $sourceChild) {
            $childVerify = Get-Item -LiteralPath $sourceChild -Force
            Write-Log "Verified child ${name}: LinkType=$($childVerify.LinkType) Target=$($childVerify.Target -join ', ')"
        }
    }
    Write-Log "Backup kept at: $backup"
    Write-Log "Fallback child junctions used: $usedFallback"
    Write-Log 'Marvis home migration finalization completed.'
} catch {
    Write-Log "Verification failed: $($_.Exception.Message)"
    throw
}
