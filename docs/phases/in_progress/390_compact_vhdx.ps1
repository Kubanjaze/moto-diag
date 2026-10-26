& {
$d = "Ubuntu-26.04"; $ok = $true; $why = @()
$key = Get-ChildItem "HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss" | ? { (Get-ItemProperty $_.PSPath).DistributionName -eq $d }
$vhd = Join-Path (Get-ItemProperty $key.PSPath).BasePath "ext4.vhdx"
$free0 = [math]::Round((Get-PSDrive C).Free/1GB,1)
"before: C: free $free0 GB"
$busy = foreach ($w in "pytest","bwrap","regression.sh") { wsl -d $d -u root -- pgrep -fa $w }
if ($busy) { "SOMETHING IS OFF: the fleet is working right now, nothing was changed. Wait for Claude to say it is safe."; return }
wsl -d $d -u root -- sh /home/lilcu/Projects/moto-diag/ops/desktop/install_fstrim_sudoers.sh
$rules = (wsl -d $d -u lilcu -- sudo -n -l) -join " "
if ($rules -notmatch "NOPASSWD: /usr/sbin/fstrim -v /") { $ok = $false; $why += "the fleet was not given its one fstrim command" }
wsl -d $d -u root -- systemctl stop motodiag-fleet.service motodiag-api.service
wsl -d $d -u root -- cp -p /home/lilcu/motodiag/live/motodiag.db "/mnt/c/Users/lilcu/motodiag-live-before-sparse.db"
if (-not (Test-Path "C:\Users\lilcu\motodiag-live-before-sparse.db")) { "SOMETHING IS OFF: could not copy the live database to C:, nothing else was changed"; wsl -d $d -u root -- systemctl start motodiag-api.service motodiag-fleet.service; return }
wsl --shutdown; Start-Sleep 10
wsl --manage $d --set-sparse true
$sparse = ((Get-Item $vhd).Attributes -band [IO.FileAttributes]::SparseFile) -ne 0
if (-not $sparse) {
  $ok = $false; $why += "WSL did not mark the disk image sparse"
  try {
    Mount-VHD -Path $vhd -ReadOnly -NoDriveLetter -ErrorAction Stop
    try { Optimize-VHD -Path $vhd -Mode Full -ErrorAction Stop } finally { Dismount-VHD -Path $vhd }
  } catch { $why += "compacting failed: $($_.Exception.Message)" }
}
Start-ScheduledTask -TaskPath "\motodiag\" -TaskName "fleet-boot"; Start-Sleep 60
if ($sparse) { wsl -d $d -u lilcu -- sudo -n /usr/sbin/fstrim -v / }
$svc = (wsl -d $d -- systemctl is-active motodiag-fleet.service motodiag-api.service) -join " "
if ($svc -ne "active active") { $ok = $false; $why += "the services are '$svc', not 'active active'" }
$free1 = [math]::Round((Get-PSDrive C).Free/1GB,1)
"after:  C: free $free1 GB (got back $([math]::Round($free1-$free0,1)) GB); disk image sparse: $sparse"
if ($free1 -le $free0) { $ok = $false; $why += "C: did not get any space back" }
if ($ok) { "ALL GOOD: the disk image is sparse, C: got space back, and Ubuntu is running again" } else { "SOMETHING IS OFF: " + ($why -join "; ") }
}
