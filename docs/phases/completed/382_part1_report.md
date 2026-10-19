# Phase 382, part 1: home desktop readiness report

Written 2026-10-12 by Claude Code on DESKTOP-76S9BQV, from a session that was not at the repository root.
Part 2 runs inside WSL2 Ubuntu-26.04 as user `lilcu`; this file is `~/382_part1_report.md` there.

## 1. Measurements (before any change)

### Machine
| Figure | Value | Command |
|---|---|---|
| Edition / version / build | Windows 11 Pro, 26H2, build 26300.9550 | `(Get-CimInstance Win32_OperatingSystem).Caption`; `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion` (DisplayVersion, CurrentBuild, UBR). The registry ProductName says "Windows 10 Pro", a known Windows 11 quirk. |
| CPU | AMD Ryzen 9 3950X, 16 cores / 32 threads | `Get-CimInstance Win32_Processor` |
| RAM | 63.9 GB | `Get-CimInstance Win32_ComputerSystem` (TotalPhysicalMemory) |
| Free disk | C: 111.9 GB free of 930.3 GB | `Get-CimInstance Win32_LogicalDisk -Filter DriveType=3` |
| Virtualization in firmware | **Off** (VirtualizationFirmwareEnabled False, HypervisorPresent False; `systeminfo`: "Virtualization Enabled In Firmware: No") | `Win32_Processor`, `Win32_ComputerSystem`, `systeminfo` |
| Motherboard | ASUS ROG STRIX B550-F GAMING (WI-FI) | `Get-CimInstance Win32_BaseBoard` |

### WSL and Docker
- WSL 2.0.14.0, kernel 5.15.133.1-1, default version 2, **no distributions** (`wsl --status`, `wsl --version`, `wsl -l -v` → `WSL_E_DEFAULT_DISTRO_NOT_FOUND`).
- Windows features enabled: Microsoft-Windows-Subsystem-Linux, VirtualMachinePlatform, Microsoft-Hyper-V-All (`Get-CimInstance Win32_OptionalFeature`).
- Docker Desktop 4.27.2 installed (Docker 25.0.3), unusable without a hypervisor (uninstall registry; `docker --version`).

### Tools (Windows)
- git: not installed. gh: not installed. Tailscale: not installed. Claude Code CLI: not on PATH (`Get-Command`).
- Python: only the Microsoft Store Python 3.11.9; no `py` launcher (`python --version`; `sys.executable`).

### Power and updates (AC; desktop, no battery)
- Power plan Ultimate Performance; sleep after **0 (never)**, hibernate after **0 (never)** (`powercfg /getactivescheme`; `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` / `HIBERNATEIDLE`).
- Windows Update active hours 09:00 to 03:00, smart active hours on; `IsExpedited` 1 (`HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings`).
- `NoAutoRebootWithLoggedOnUsers` 0: it restarts even with a user signed in (`HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU`).
- Automatic sign-in: **off** (Winlogon `AutoAdminLogon` unset, no DefaultUserName). After an update restart, nobody is signed in.

### Network
- Active network "Mercy" (Ethernet), profile **Public**; firewall enabled on Domain, Private and Public (`Get-NetConnectionProfile`, `Get-NetFirewallProfile`).
- Non-loopback listeners (`Get-NetTCPConnection -State Listen`): Windows RPC 135, SMB 139/445, 5040, Delivery Optimization 7680, RPC 49664-49668 and 49687, Steam 0.0.0.0:27036, GameManagerService3 :::49672.

## 2. The pick, in the owner's words

> "yeah i agree with A, i am pretty sure that i have that on this system but check, verify and if not, install"

Option A: WSL2 with Ubuntu. Firmware virtualization was off; the owner enabled SVM in UEFI ("SVM turned on, andale").

## 3. Every change made to this machine

| # | Change | Who / how | Verified by |
|---|---|---|---|
| 1 | UEFI: **SVM Mode enabled** | Owner, by hand in the BIOS | `VirtualizationFirmwareEnabled True`, `HypervisorPresent True`, `systeminfo`: "A hypervisor has been detected" |
| 2 | **WSL updated** 2.0.14.0 → 3.0.3.0 (kernel 6.18.54.1-1) | `wsl --update`, elevated (UAC approved by owner) | `wsl --version` |
| 3 | **Ubuntu-26.04 LTS installed** (26.04.1), default distribution, WSL 2; user `lilcu` created by owner | `wsl --install -d Ubuntu-26.04 --no-launch`, first launch by owner | `wsl -l -v`; inside: systemd is PID 1, `systemctl is-system-running` = running; `/etc/wsl.conf` has `systemd=true`, `default=lilcu` |
| 4 | **Tailscale for Windows 1.104.1** installed; service Running, startup Automatic; signed in by owner; serving nothing | `winget install --id Tailscale.Tailscale -e --accept-package-agreements` (accepted Tailscale's license; flagged to the owner afterwards) | `Get-Service Tailscale`; `tailscale status --json` BackendState Running (signed in: yes); `tailscale serve status` / `funnel status`: "No serve config" |
| 5 | Ubuntu git config: `core.autocrlf=false`, `core.eol=lf` | `git config --global` | `git config --global --get` |
| 6 | **uv 0.13.0** in `~/.local/bin`; **CPython 3.14.5** at `~/.local/share/uv/python/cpython-3.14.5-linux-x86_64-gnu/` | Astral installer; `uv python install 3.14.5` | `uv --version`; `python3.14 --version` = 3.14.5. Ubuntu's own `/usr/bin/python3.14` is 3.14.4 and is not used. |
| 7 | **gh 2.102.0** in `~/.local/bin` | Release tarball from github.com/cli/cli, SHA-256 checked against the release checksums | `gh --version` |
| 8 | gh signed in as **Kubanjaze**; `gh auth setup-git` (git credential helper = gh) | Owner, device flow | `gh auth status` exit 0 (signed in: yes); push permission true on moto-diag, moto-diag-mobile, workspace-docs. gh noted the token is stored in plain text in `~/.config/gh/hosts.yml` (no keyring in WSL). |
| 9 | **Claude Code 2.1.296** in `~/.local/bin/claude` | Anthropic native installer | `claude --version` |
| 10 | Repositories cloned to `~/Projects/` (Linux filesystem, not /mnt/c): moto-diag (master @ 77755a4), moto-diag-mobile (main @ 0074eb9), workspace-docs (main @ 4a5ca20) | `git clone https://github.com/Kubanjaze/<repo>.git` | clean `git status`; `git ls-files --eol` shows 0 CRLF files in each |
| 11 | `moto-diag/.venv` on Python 3.14.5; `pip install -e ".[dev]"` as README says, then **`pip install -e ".[all,server]"`** | see §4 | `.venv/bin/python --version` 3.14.5 |

Not changed: Windows power settings (sleep and hibernate were already off on AC), Windows Update, firewall, scheduled tasks, auto sign-in, Docker Desktop (left installed, not started).

### Still open at the time of writing
- ~~Tailscale "Run unattended"~~: **done**. The owner turned it on from the tray; verified with `"ForceDaemon": true` in `tailscale debug prefs`.
- **Claude Code sign-in inside Ubuntu**: the owner signs in on first `claude` run.

## 4. wholetree result

Command: `.claude/skills/closeout/wholetree.sh` (fast mode) at `~/Projects/moto-diag`.

**Run 1, `.venv` with `.[dev]` only (as the README says):** exit **1**, 7 failed, 1647 passed, 10 skipped, 1 error (57.56 s).
Every failure was `ModuleNotFoundError: No module named 'fastapi'`. The collected-test-floor test saw 9443 of 10838 because modules that can't import aren't collected. Cause: the `.[dev]` extra holds no API dependencies. The repo's own history (phase_log.md; F48_phase_log.md) records the Mac `.venv` as `.[all]`. `.[server]` added because the live server needs it (api, ai, vision, push, reports, payments).

**Run 2, after `pip install -e ".[all,server]"`:** exit **1**: **1 failed, 1673 passed, 10 skipped**, 19 warnings (56.04 s).
- Failing: `tests/test_phase244J_guidance_surface.py::TestTheEndpointExists::test_the_route_is_registered`.
- The test flattens `app.routes` and finds only the four docs routes. This venv resolved **fastapi 0.143.0 / starlette 1.7.0**, where included routers appear in `app.routes` as `_IncludedRouter` objects (21 entries, types `Route` and `_IncludedRouter`) and not as their individual routes.
- The route itself exists: `app.openapi()` lists 81 paths, including `POST /v1/sessions/{session_id}/videos/{video_id}/ask`, and the other 19 tests in that file, which call the endpoint, pass.
- **Read as a machine difference until the Mac reproduces it.** To compare, run `.venv/bin/pip show fastapi starlette` on the Mac. If the Mac is on an older FastAPI, the difference is the dependency version this machine resolved, not the code.

Full log: `~/Projects/moto-diag/.git/motodiag_wholetree/last_fast.log`.

## 5. Facts part 2 has to prove (not measurable before setup)
- The API starting at boot, and after a Windows Update restart, with nobody signed in: a Windows scheduled task at startup that starts WSL and keeps it running (`vmIdleTimeout`), plus a systemd unit in Ubuntu, bound to 127.0.0.1.
- Whether `tailscale serve` runs on the Windows client (installed) or inside Ubuntu.
- Where the live database lives: inside the Ubuntu filesystem, outside the repositories.

## 6. Start part 2
Inside the Ubuntu shell:

    cd ~/Projects/moto-diag && claude "$(cat docs/prompts/382_live_on_the_home_desktop.txt)"

From Windows PowerShell:

    wsl -d Ubuntu-26.04 --cd ~/Projects/moto-diag -- bash -lc 'claude "$(cat docs/prompts/382_live_on_the_home_desktop.txt)"'
