#!/usr/bin/env bash
# fence.sh — one fleet stage inside bubblewrap (Phase 388).
#
#   fence.sh --clone DIR --run DIR --workspace-docs DIR [--net model|none] -- CMD [ARG...]
#
# Runs CMD with the clone as its working directory and exits with CMD's code.
# What CMD can see (measured in 388_step0.md, S0-5):
#   /fleet/moto-diag        the clone, writable
#   /fleet/run              the run directory, writable (HOME, TMPDIR and
#                           CLAUDE_CONFIG_DIR live in it)
#   /fleet/workspace-docs   read-only, so CLAUDE.md's ../workspace-docs import
#                           resolves from the clone
#   /fleet/bin/claude       the claude binary, read-only
#   /usr, /etc              read-only; private /proc, /dev and /tmp
# and nothing else: there is no /home, so the operator's home, ~/.config,
# ~/.ssh and every credential in it are not there to read. / and /fleet are
# remounted read-only.
#
# --net model (the default): fence_net.py's gate outside the fence lets
# CONNECT to the model API through and refuses everything else; --net none:
# no network at all.
#
# The environment is built from nothing. CLAUDE_CODE_OAUTH_TOKEN crosses when
# the caller set it, inherited and never on a command line (any process can
# read another's argv). Nothing else of the caller's environment crosses.
#
# Exit 2, before bwrap starts: no bwrap; the clone is not a git work tree, or
# is the repository this script lives in (rule 5: never a checkout someone
# works in); no run directory; no working-rules.md under --workspace-docs (a
# fence without it runs with no workspace rules, S0-2).
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
NET_PORT=18080
INSIDE=/fleet/moto-diag

refuse() { echo "fence.sh: refused: $*" >&2; exit 2; }

clone="" run="" wsdocs="" net=model
while [ $# -gt 0 ]; do
  case "$1" in
    --clone) clone=$2; shift 2 ;;
    --run) run=$2; shift 2 ;;
    --workspace-docs) wsdocs=$2; shift 2 ;;
    --net) net=$2; shift 2 ;;
    --) shift; break ;;
    *) refuse "unknown argument $1" ;;
  esac
done
[ $# -gt 0 ] || refuse "no command after --"
case "$net" in model|none) ;; *) refuse "--net is model or none, not $net" ;; esac

BWRAP=$(command -v bwrap) || refuse "bwrap is not installed"
[ -n "$clone" ] && [ -d "$clone" ] || refuse "no clone directory: ${clone:-unset}"
clone=$(cd "$clone" && pwd -P)
[ "$(git -C "$clone" rev-parse --show-toplevel 2>/dev/null)" = "$clone" ] \
  || refuse "the clone is not a git work tree: $clone"
self=$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || true)
[ -n "$self" ] && [ "$(cd "$self" && pwd -P)" = "$clone" ] \
  && refuse "the clone is the repository fence.sh runs from: $clone"
[ -n "$run" ] && [ -d "$run" ] || refuse "no run directory: ${run:-unset}"
run=$(cd "$run" && pwd -P)
[ -n "$wsdocs" ] && [ -f "$wsdocs/claude/working-rules.md" ] \
  || refuse "no claude/working-rules.md under --workspace-docs ${wsdocs:-unset}"
wsdocs=$(cd "$wsdocs" && pwd -P)

mkdir -p "$run/home" "$run/tmp" "$run/claude"
# The operator's 2026-09-23 approval of this import, for the fence's clone
# path; without it print mode loads no external import (S0-2). Merged, so a
# resumed stage keeps its config.
/usr/bin/python3 - "$run/claude/.claude.json" "$INSIDE" <<'PY'
import json, pathlib, sys
path, project = pathlib.Path(sys.argv[1]), sys.argv[2]
config = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
config.setdefault("projects", {}).setdefault(project, {}).update(
    hasClaudeMdExternalIncludesApproved=True, hasClaudeMdExternalIncludesWarningShown=True)
path.write_text(json.dumps(config, indent=2), encoding="utf-8")
PY

args=(--unshare-all --die-with-parent --new-session
      --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib
      --symlink usr/lib64 /lib64 --symlink usr/sbin /sbin
      --ro-bind /etc /etc --proc /proc --dev /dev --tmpfs /tmp
      --tmpfs /fleet
      --bind "$clone" "$INSIDE" --bind "$run" /fleet/run
      --ro-bind "$wsdocs" /fleet/workspace-docs
      --ro-bind "$HERE/fence_net.py" /fleet/lib/fence_net.py)
if claude_bin=$(readlink -f "$(command -v claude 2>/dev/null)" 2>/dev/null) && [ -x "$claude_bin" ]; then
  args+=(--ro-bind "$claude_bin" /fleet/bin/claude)
fi

netdir=""
proxy_pid=""
cleanup() {
  [ -n "$proxy_pid" ] && kill "$proxy_pid" 2>/dev/null || true
  [ -n "$netdir" ] && rm -rf "$netdir" || true
}
trap cleanup EXIT

inner=("$@")
if [ "$net" = model ]; then
  # A short directory: a unix socket path is limited to 108 bytes (S0-5).
  netdir=$(mktemp -d /tmp/fleet-net.XXXXXX)
  /usr/bin/python3 "$HERE/fence_net.py" proxy "$netdir/gate.sock" "$run/net.log" &
  proxy_pid=$!
  for _ in $(seq 50); do [ -S "$netdir/gate.sock" ] && break; sleep 0.1; done
  [ -S "$netdir/gate.sock" ] || refuse "the network gate did not start"
  args+=(--bind "$netdir/gate.sock" /fleet/net.sock
         --setenv HTTPS_PROXY "http://127.0.0.1:$NET_PORT" --setenv https_proxy "http://127.0.0.1:$NET_PORT"
         --setenv HTTP_PROXY "http://127.0.0.1:$NET_PORT" --setenv http_proxy "http://127.0.0.1:$NET_PORT")
  inner=(/usr/bin/python3 /fleet/lib/fence_net.py inside "$NET_PORT" /fleet/net.sock -- "$@")
fi

args+=(--remount-ro /fleet --remount-ro /
       --setenv HOME /fleet/run/home --setenv TMPDIR /fleet/run/tmp
       --setenv CLAUDE_CONFIG_DIR /fleet/run/claude --setenv PATH /fleet/bin:/usr/bin:/bin
       --setenv TERM dumb --setenv LANG C.UTF-8
       --setenv CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 1
       --chdir "$INSIDE")

# The environment from nothing, by builtins: bwrap inherits only the token.
status=0
(
  for var in $(compgen -e); do
    [ "$var" = CLAUDE_CODE_OAUTH_TOKEN ] || unset "$var" 2>/dev/null || true
  done
  exec "$BWRAP" "${args[@]}" -- "${inner[@]}"
) || status=$?
exit "$status"
