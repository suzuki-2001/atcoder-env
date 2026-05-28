.DEFAULT_GOAL := help

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# `UID` is readonly on macOS bash/zsh, so route compose vars through `env`.
HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")
DC   := env UID=$(HOST_UID) GID=$(HOST_GID) $(if $(LANGUAGES),LANGUAGES=$(LANGUAGES),) $(COMPOSE)
EXEC := $(DC) exec atcoder
PY   := $(EXEC) python3 /work/scripts/atcoder_api.py

# Positional args after the target (e.g. `make new abc400 a`).
# Use `=` (deferred) so $@ is evaluated per-recipe, not at parse time.
ARGS = $(filter-out $@,$(MAKECMDGOALS))

OPEN := $(shell command -v open >/dev/null 2>&1 && echo open || echo xdg-open)

# Reject paths with shell metachars (used in cd /work/contests/<path>).
SAFE_PATH = case "$(1)" in *[!a-zA-Z0-9_/.-]*) echo "invalid path: $(1)"; exit 1;; esac

.PHONY: help build up down restart setup login whoami doctor shell status \
        new test submit open contests tasks ac todo cache clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

build:   ## build the Docker image
	$(DC) build

up:      ## start the container (detached)
	$(DC) up -d

down:    ## stop the container
	$(DC) down

restart: down up ## restart the container

setup: build up ## first-time setup
	@echo ""
	@echo "Next: 'make login' to paste your REVEL_SESSION cookie."

login:   ## paste REVEL_SESSION cookie via aclogin
	@echo "============================================================"
	@echo " 1. Log in to https://atcoder.jp in your browser"
	@echo " 2. DevTools -> Application -> Cookies -> copy REVEL_SESSION"
	@echo " 3. Paste it at the prompt below"
	@echo "============================================================"
	$(EXEC) aclogin

whoami:  ## check session validity & show handle
	$(PY) whoami

doctor:  ## full diagnostics: tools, MiB patch, cookie, AtCoder reachability
	$(PY) doctor

shell:   ## bash inside the container
	$(EXEC) bash

status:  ## container status
	$(DC) ps

new:     ## make new <contest> [task]   [T=cpp|py|c|go|rust] [CHOICE=all|manual|next|rest|none]
	@test -n "$(word 1,$(ARGS))" || { echo "usage: make new <contest> [task]   [T=cpp|py|c|go|rust] [CHOICE=...]"; exit 1; }
	@$(call SAFE_PATH,$(word 1,$(ARGS)))
	@$(if $(word 2,$(ARGS)),$(call SAFE_PATH,$(word 2,$(ARGS))))
	@$(PY) precheck
	$(EXEC) sh -c 'cd /work/contests && acc new $(ARGS) \
	  $(if $(T),--template $(T),) \
	  $(if $(CHOICE),--choice $(CHOICE),)'
	@contest="$(word 1,$(ARGS))"; task="$(word 2,$(ARGS))"; \
	if [ -n "$$task" ]; then \
	  $(PY) problem "$$contest" "$$task" || true; \
	else \
	  for d in contests/$$contest/*/; do \
	    [ -d "$$d" ] || continue; \
	    $(PY) problem "$$contest" "$$(basename $$d)" || true; \
	  done; \
	fi

test:    ## make test <contest>/<task>   (auto-detects main.{cpp,py,c,go,rs})
	@test -n "$(word 1,$(ARGS))" || { echo "usage: make test <contest>/<task>"; exit 1; }
	@$(call SAFE_PATH,$(word 1,$(ARGS)))
	$(EXEC) sh -c 'cd "/work/contests/$(word 1,$(ARGS))" && \
	  if   [ -f main.cpp ]; then g++ -std=gnu++20 -O2 -DLOCAL -o a.out main.cpp && oj t -c ./a.out; \
	  elif [ -f main.py  ]; then oj t -c "python3 main.py"; \
	  elif [ -f main.c   ]; then gcc -std=c17 -O2 -DLOCAL -lm -o a.out main.c && oj t -c ./a.out; \
	  elif [ -f main.go  ]; then go build -o a.out main.go && oj t -c ./a.out; \
	  elif [ -f main.rs  ]; then rustc -O main.rs -o a.out && oj t -c ./a.out; \
	  else echo "no main.{cpp,py,c,go,rs} in $(word 1,$(ARGS))"; exit 1; \
	  fi'

submit:  ## make submit <contest>/<task>
	@test -n "$(word 1,$(ARGS))" || { echo "usage: make submit <contest>/<task>"; exit 1; }
	@$(call SAFE_PATH,$(word 1,$(ARGS)))
	@$(PY) precheck
	$(EXEC) sh -c 'cd "/work/contests/$(word 1,$(ARGS))" && acc submit'

open:    ## make open <contest>/<task>   — open problem.html in your browser
	@test -n "$(word 1,$(ARGS))" || { echo "usage: make open <contest>/<task>"; exit 1; }
	@$(call SAFE_PATH,$(word 1,$(ARGS)))
	@f="contests/$(word 1,$(ARGS))/problem.html"; \
	 if [ -f "$$f" ]; then $(OPEN) "$$f"; \
	 else echo "$$f not found — run 'make new' first"; exit 1; fi

contests: ## list recent contests
	$(PY) contests

tasks:   ## make tasks <contest>   — list problems + your AC status
	@test -n "$(word 1,$(ARGS))" || { echo "usage: make tasks <contest>"; exit 1; }
	@$(call SAFE_PATH,$(word 1,$(ARGS)))
	$(PY) tasks $(word 1,$(ARGS))

ac:      ## show your AC stats
	$(PY) ac

todo:    ## recommend unsolved problems by difficulty
	$(PY) todo

cache:   ## show cached API blobs (use `make cache CLEAR=1` to wipe)
	$(PY) cache $(if $(CLEAR),--clear,)

clean:   ## wipe contests/ (asks first)
	@read -p "Wipe contests/? [y/N] " yn; \
	 [ "$$yn" = "y" ] && find contests -mindepth 1 ! -name .gitkeep -delete || echo "aborted"

# Catch-all so `make new abc400 a` doesn't try to build literal targets
# `abc400` and `a`.
%:
	@:
