.DEFAULT_GOAL := help
SHELL         := /bin/bash

CYAN  := \033[0;36m
GREEN := \033[0;32m
NC    := \033[0m

.PHONY: help
help:
	@echo -e ""
	@echo -e "  $(CYAN)Lightshow$(NC)"
	@echo -e ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ \
		{ printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo -e ""

.PHONY: install
install: ## Installs dependencies using uv.
	uv sync --locked --all-extras

.PHONY: update
update: ## Fetches update from github
	git pull

.PHONY: dev
dev: ## Run the software
	uv run lightshow

.PHONY: build-windows
build-windows: ## Build app using pyinstaller
	uv run pyinstaller lightshow.spec

.PHONY: installer-windows
installer-windows: ## Make windows installer using NSIS
	cd installer && makensis /DPRODUCT_VERSION=$(version) lightshow.nsi

.PHONY: hooks
hooks: ## Install hooks
	uv run pre-commit install
