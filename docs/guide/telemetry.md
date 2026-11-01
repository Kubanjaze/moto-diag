# Crash reports: being told when the server fails

When something inside the server breaks while a mechanic is using the app,
the mechanic sees "Internal server error" and nothing else. Without crash
reports, you find out only if someone phones you. With them, each crash
appears on your Sentry dashboard within seconds, with the request id that
the mechanic's error screen shows, so you can match the two.

The dashboard is Sentry's website, outside this repository. Alert rules
(an email when a crash comes in, for example) are set up there.

## What a crash report carries

Only these, and nothing else:

- the kind of error (for example `RuntimeError`);
- the error's message, with every login session token, email address and
  phone number blanked out, and cut to 500 characters;
- where in the code it happened: file, function and line number, with no
  values from inside the program;
- the request id, the method (GET, POST and so on), and the route's
  pattern, for example `/v1/shop/{shop_id}/work-orders/{wo_id}`, never the
  real numbers in the address;
- the response status (500), the MotoDiag version, the environment name and
  the computer's name.

**Never sent:** what a person typed or uploaded, the address's query part,
login cookies or keys, who was logged in, customer names, bike owners or
anything else from the database.

## Request timings

One request in ten is also timed: the same route pattern, the method, the
status and how long it took. That is what Sentry's "Performance" page shows.
`/healthz` and browser "preflight" checks are never timed.

## The phone app sends nothing

Crash reports come only from the server. The phone app has no crash or
analytics software in it, and no screen recording ("session replay") exists
anywhere.

## Turning it on and off

Crash reports are on when one line is in the server's settings file on the
home desktop, `~/.config/motodiag/server.env` (only your user can read it,
mode 600):

```
MOTODIAG_SENTRY_DSN=<the DSN that Sentry shows for the project>
```

The DSN is the project's address and key in one. Keep it only in that file:
never type it into a chat, an issue or a command line. To turn reports off,
delete the line and restart the server:

```bash
systemctl --user restart motodiag-api.service
```

`motodiag config show` masks the DSN, so it is safe to run.

## Is it on, and does it work?

On the home desktop, in the Ubuntu terminal, give the terminal the server's
own settings first, once per window:

```bash
export PATH="$HOME/motodiag/server/.venv/bin:$PATH"
set -a; . ~/.config/motodiag/server.env; set +a
```

Then:

```bash
motodiag telemetry status
```

prints `telemetry: on` and the project it reports to (never the key), or
says it is off.

```bash
motodiag telemetry check
```

sends one test event to Sentry, a message reading "telemetry check from
<computer> at <time>", and prints its event id. It says what it will send
before it sends it. It ends with `sent:` when Sentry accepted it; open the
project in Sentry and look for that event id. It ends with `not sent:` and
the reason (for example status 401, a wrong key) otherwise.

When the server starts, its log line `motodiag API ready` ends with
`telemetry=on` and the project, or `telemetry=off`.
