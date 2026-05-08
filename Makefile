.DEFAULT_GOAL := help
SHELL         := /bin/bash

CYAN  := \033[0;36m
GREEN := \033[0;32m
NC    := \033[0m

.PHONY: help
help:
	@echo ""
	@echo "  $(CYAN)Lightshow$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ \
	    { printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

.PHONY: install
install:
	uv sync --locked --all-extras

.PHONY: update
update:
	git pull

.PHONY: dev
dev:
	uv run lightshow

.PHONY: build-windows
build-windows:
	uv run pyinstaller lightshow.spec

.PHONY: installer-windows
installer-windows:
	cd installer && makensis /DPRODUCT_VERSION=$(version) lightshow.nsi

.PHONY: hooks
hooks:
	uv run pre-commit install
