# atcoder-env

Dockerised AtCoder local environment. `atcoder-cli` (acc) + `online-judge-tools` (oj) + `aclogin`, with the MiB-unit patch and the Cloudflare-cookie workaround baked into the image.

## Why

Out-of-the-box install no longer works:

- **Cloudflare Turnstile** (Apr 2025) blocks `oj login` / `acc login`. See [oj#934](https://github.com/online-judge-tools/oj/issues/934).
- **MB → MiB** display change (around ABC408, Jun 2025) breaks `oj submit` with `AssertionError: assert parsed_memory_limit`. See [api-client#172](https://github.com/online-judge-tools/api-client/issues/172).

Neither is fixed upstream as of 2026-05. This repo bakes the community workaround into a container so nothing touches the host.

## Setup

```sh
make setup     # build + up
make login     # paste REVEL_SESSION cookie
```

### Cookie login

1. Log in to <https://atcoder.jp> in your browser.
2. DevTools → Application → Cookies → copy the `REVEL_SESSION` value.
3. `make login` and paste.

Session lasts ~6 months and is kept in named volumes (`acc-session`, `oj-session`). Don't log out from the browser — that invalidates the cookie. `make whoami` verifies the session is still alive.

## Daily use

```sh
make new abc400              # fetch all tasks (default)
make new abc400 a            # one task
make new abc400 a T=py       # Python template
make new abc400 CHOICE=manual  # interactive task picker (also: next|rest|none)

$EDITOR contests/abc400/a/main.cpp
make test   abc400/a
make submit abc400/a
```

| Command | What it does |
|---|---|
| `make new <contest> [task]` | `acc new` + sample + `problem.html` download |
| `make test <contest>/<task>` | build (g++ / python3) + `oj t` |
| `make submit <contest>/<task>` | `acc submit` |
| `make open <contest>/<task>` | open `problem.html` in your default browser |
| `make whoami` | check session validity, show your handle |
| `make shell` | bash in the container |
| `make up` / `make down` / `make restart` | container lifecycle |
| `make clean` | wipe `contests/` (confirms first) |

### Browsing & stats (uses [AtCoder Problems API](https://kenkoooo.com/atcoder/))

```sh
cp .env.example .env       # then edit ATCODER_USER=<your_handle>

make contests              # recent contests (ABC/ARC/AGC/AHC, newest first)
make tasks abc400          # problems in a contest + AC mark
make ac                    # your rating, AC count, recent ACs
make todo                  # unsolved problems sorted by difficulty
```

`make ac` and `make todo` need `ATCODER_USER` set; `make tasks` works without it (just no AC column).

`make` alone or `make help` lists everything.

## Layout

```
contests/
  abc400/
    a/
      main.cpp
      problem.html
      test/sample-1.{in,out}
    b/, c/, ...
  ahc045/, arc220/, agc070/
```

`acc` keys off the contest ID, so ABC / AHC / ARC / AGC all land under their own directory.

## Templates

Edit `templates/cpp/main.cpp` or `templates/py/main.py` directly — they're mounted into the container and copied into `acc`'s config dir on every container start. Run `make restart` to pick up edits.

Add a new template by dropping `templates/<name>/{template.json, main.<ext>}`.

Default template: `cpp`. Switch per-call with `T=py`, or globally via `DEFAULT_TEMPLATE` in `docker-compose.yml`.

## What's in the image

- Ubuntu 24.04, g++ 13, Python 3.12, Node 20
- `atcoder-cli` (npm) + `online-judge-tools` + `aclogin` (pip, with `--break-system-packages`)
- AC Library at `/opt/ac-library` (added to `CPLUS_INCLUDE_PATH`)
- MiB patch applied to `onlinejudge/service/atcoder.py` at build time
- Default compile flags for `make test`: `g++ -std=gnu++20 -O2 -DLOCAL`
