# Installing MotoDiag

Three ways in, depending on what you are. Every command below was run on
a clean machine state while writing this page.

| You are | Use |
|---|---|
| A mechanic who wants the CLI | [pipx](#mechanic-the-cli) |
| Running the API for a shop or the iOS app | [Docker](#shop-the-api) or pip with the `api` extra |
| Working on MotoDiag | [source checkout](#developer-from-source) |

## Mechanic: the CLI

`pipx` installs the CLI into its own isolated environment and puts
`motodiag` on your PATH, without touching your system Python:

```bash
brew install pipx        # macOS; or: python3 -m pip install --user pipx
pipx ensurepath
pipx install motodiag
motodiag db init
```

`db init` creates your database and loads the starter data — DTC
definitions, symptoms, and 766 curated known issues, all shipped
inside the package. Check it worked:

```bash
motodiag --version
motodiag code P0115
```

If `code P0115` says *"No DB entry — heuristic classification only"*,
`db init` did not load the knowledge base. Re-run it and read the
output; it will tell you if the seed data is missing.

Plain `pip` works too, but installs into whatever environment is active:

```bash
python3 -m venv ~/.motodiag-venv
source ~/.motodiag-venv/bin/activate
pip install motodiag
```

### Where your data lives

An installed MotoDiag keeps its database in your user data directory:

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/motodiag/motodiag.db` |
| Linux | `$XDG_DATA_HOME/motodiag/`, else `~/.local/share/motodiag/` |

Override with `MOTODIAG_DB_PATH`. `motodiag config paths` prints the
resolved locations. **Back this file up** — it is your entire shop
history, and nothing else holds a copy.

### Optional extras

The base install is deliberately small. Add what you need:

```bash
pipx install "motodiag[ai]"        # AI-assisted diagnosis (Anthropic)
pipx install "motodiag[hardware]"  # OBD-II adapters
pipx install "motodiag[api,vision]"  # HTTP API + photo processing
```

| Extra | Gives you | Without it |
|---|---|---|
| `ai` | `motodiag diagnose`, `quick` | Fault-code lookup, KB and the shop workflow all still work |
| `hardware` | `motodiag hardware` — adapters, live PIDs | Everything except talking to an ECU |
| `api` | `motodiag serve` | No HTTP API, so no iOS app |
| `vision` | Photo processing on the API | The API runs; photo endpoints fail, naming this extra |
| `push` | APNs notifications | Notifications are queued but not sent |

## Shop: the API

The iOS app needs an HTTP API to talk to.

> **The container has not been built or run.** It is written and
> reviewed but Docker was unavailable when it was authored — see F76.
> The pip route below *has* been verified end to end.

```bash
docker compose up --build
curl localhost:8000/healthz
```

Or with pip:

```bash
python3 -m venv /opt/motodiag
/opt/motodiag/bin/pip install "motodiag[api,vision,push]"
/opt/motodiag/bin/motodiag serve --host 0.0.0.0
```

`serve` applies any pending schema migrations before it binds, so a
fresh install needs no separate init step.

```bash
curl -s localhost:8000/healthz
```

```json
{"status": "ok", "schema_version": 50, "detail": null}
```

Then make a key for the app:

```bash
motodiag apikey create --user 1 --name iphone
```

### Before it faces anything real

`motodiag serve` on a laptop is a development setup. For an install a
customer or an employee will touch:

- **`MOTODIAG_ENV=prod`** — turns on the startup guards. It will refuse
  to start on the fake billing provider, which is the point.
- **`MOTODIAG_BILLING_PROVIDER=stripe`** plus
  `MOTODIAG_STRIPE_WEBHOOK_SECRET`. The `fake` provider accepts a
  hardcoded webhook signature on an unauthenticated route.
- **`MOTODIAG_PUBLIC_BASE_URL`** — the origin customer share links are
  built from. The default is localhost, and a link built from localhost
  resolves to the *customer's own phone*.
- **`MOTODIAG_API_CORS_ORIGINS`** — defaults to localhost dev origins.
- **TLS in front of it.** Note that rate limiting currently keys on the
  socket address, so behind a proxy without forwarded-header handling
  every anonymous caller shares one bucket (F71).

## Developer: from source

```bash
git clone https://github.com/Kubanjaze/moto-diag.git
cd moto-diag
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,api,ai,hardware,vision,push]"
motodiag db init
pytest -q
```

A source checkout keeps its database at the repo's `data/motodiag.db`
rather than your user data directory, so development data never mixes
with a real install. See [contributing](../contributing.md).

## Upgrading

```bash
pipx upgrade motodiag
```

Your database is not touched by an upgrade, and migrations apply
automatically on the next `db init` or `serve`. Migrations are
forward-only in practice: take a copy of the database file before a
major upgrade if the data matters.

## Uninstalling

```bash
pipx uninstall motodiag
```

That leaves your data behind on purpose. To remove it:

```bash
rm -rf ~/Library/Application\ Support/motodiag   # macOS
rm -rf ~/.local/share/motodiag                   # Linux
```

## What about a standalone binary?

There isn't one, deliberately. Freezing a CLI with 24 command groups,
five optional extras and 1.5 MB of packaged data means a ~100 MB
artefact per platform plus macOS code signing and notarisation — a
large amount of fragile machinery to deliver what `pipx install
motodiag` already does: an isolated CLI on your PATH that does not
touch system Python. If you need MotoDiag on a machine without Python
at all, the Docker image is the better answer.
