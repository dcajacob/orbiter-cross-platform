$ErrorActionPreference='Stop'
$base='C:\Users\Public\RC1verify'
$work="$base\receipt"
New-Item -ItemType Directory -Path $work -Force | Out-Null
Copy-Item 'out/probe/plugins' $work -Recurse
Copy-Item 'Tests/Production/ReadOnlyRC1/exercise.py' "$base/exercise.py"
$user='OrbiterPilot'
$password=ConvertTo-SecureString ([guid]::NewGuid().ToString()+'Aa1!') -AsPlainText -Force
$account=New-LocalUser -Name $user -Password $password
if (!(Get-LocalGroupMember -SID S-1-5-32-545 | Where-Object {$_.SID -eq $account.SID})) {Add-LocalGroupMember -SID S-1-5-32-545 -Member $account}
& icacls $work /grant ("${user}:(OI)(CI)M") /Q
if ($LASTEXITCODE) {throw 'Evidence permissions'}
& icacls $env:RC1_INSTALL /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' /Q
if ($LASTEXITCODE) {throw 'Install permissions'}
& icacls "$env:RC1_INSTALL\*" /reset /T /Q | Select-Object -Last 1
if ($LASTEXITCODE) {throw 'Install child permissions'}
$cred=[pscredential]::new("$env:COMPUTERNAME\$user",$password)
$exe=(Get-Command python).Source
$p=Start-Process -Credential $cred -LoadUserProfile -FilePath $exe -WorkingDirectory $work -ArgumentList @('-B',"$base/exercise.py",$env:RC1_INSTALL,$work) -Wait -PassThru
if ($p.ExitCode) {throw "Standard-user test exited $($p.ExitCode)"}
