# Phase 389 — the operator's steps

These are yours: making the fleet its own GitHub account is a login, and
only you can make one. Nothing in the phase waits for them. Until they are
done, the trial runs under your own login, as you allowed for a planted
trial, and every other phase the fleet touches stops before its first push
and says so on its issue.

## Step 1: give the fleet its own GitHub account

**Why:** the fleet pushes branches and opens pull requests. Today
anything pushed from the desktop goes out as you, an administrator of the
repository. The fleet should push as an account that can write to this one
repository and is not an administrator of it.

### Part A, in a web browser (any computer)

1. Open a **private window** (so you stay signed in as yourself in your
   normal windows) and go to `https://github.com/signup`.
2. Make a new account:
   - **Email:** any address you can read. A Gmail "plus" address works,
     for example `kubanjaze+motodiag-fleet@gmail.com`; its mail lands in
     your normal inbox.
   - **Username:** `motodiag-fleet`, or any free name. Write it down.
   - Finish the sign-up and the email check. If GitHub asks you to turn on
     two-factor sign-in, do it.
3. Still in that private window, signed in as the new account, open
   `https://github.com/settings/tokens/new` (the "classic" token page).
   - **Note:** `motodiag fleet on the desktop`
   - **Expiration:** 90 days
   - **Scopes:** tick **only** `public_repo` (under "repo"). Nothing else.
   - Press **Generate token**. GitHub shows a token starting `ghp_` once.
     Leave the page open; you paste it in Part B.

**Never paste the token into a chat, a message or a document.**

### Part B, on the desktop, in the Ubuntu window

Paste this block. It asks for the new account's username, then for the
token (the token will not show as you paste: that is on purpose). It saves
the token where only you can read it, invites the new account to the
repository with write access (using your own login), accepts that
invitation as the new account, and checks the result.

```
read -rp "The fleet account's username: " U && read -rsp "Paste the token here (it will not show), then press Enter: " T && echo && mkdir -p ~/.config/motodiag && printf 'FLEET_GITHUB_USER=%s\nFLEET_GITHUB_TOKEN=%s\n' "$U" "$T" > ~/.config/motodiag/fleet-github.env && chmod 600 ~/.config/motodiag/fleet-github.env && gh api -X PUT "repos/Kubanjaze/moto-diag/collaborators/$U" -f permission=push > /dev/null; I=$(GH_TOKEN="$T" gh api user/repository_invitations --jq '.[] | select(.repository.full_name=="Kubanjaze/moto-diag") | .id' | head -1); [ -n "$I" ] && GH_TOKEN="$T" gh api -X PATCH "user/repository_invitations/$I" > /dev/null; L=$(GH_TOKEN="$T" gh api user --jq .login 2>/dev/null); P=$(GH_TOKEN="$T" gh api repos/Kubanjaze/moto-diag --jq '"\(.permissions.push) \(.permissions.admin)"' 2>/dev/null); S=$(GH_TOKEN="$T" gh api -i user 2>/dev/null | tr -d '\r' | sed -n 's/^[Xx]-[Oo][Aa]uth-[Ss]copes: //p'); unset T; F=~/.config/motodiag/fleet-github.env; if [ "$L" = "$U" ] && [ "$L" != "Kubanjaze" ] && [ "$P" = "true false" ] && [ "$S" = "public_repo" ] && [ "$(stat -c %a "$F")" = 600 ] && [ "$(grep -c '' "$F")" = 2 ]; then echo "ALL GOOD"; else echo "SOMETHING IS OFF (account: ${L:-none}, write and admin: ${P:-none}, scopes: ${S:-none})"; fi
```

It passes only when the token belongs to the account you named (and not
to yours), that account can write to the repository and is not an
administrator, the token's only scope is `public_repo`, and only you can
read the saved file. If it says SOMETHING IS OFF, the words in brackets
say which part.

**Then:** tell me it printed ALL GOOD. From then on the fleet pushes and
opens pull requests as that account; I check it myself with one push of
a fleet branch.

**Later, not now:** the token expires in 90 days. Making a new one and
running Part B again replaces it.
