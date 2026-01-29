VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

.PHONY: build test lint format clean

## build: create virtualenv and install all dependencies (prod + dev)
build: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio ruff
	touch $(VENV)/bin/activate

## test: run the full test suite
test: build
	$(VENV)/bin/pytest tests/ -v

## lint: static analysis with ruff
lint: build
	$(VENV)/bin/ruff check .

## format: auto-format sources with ruff
format: build
	$(VENV)/bin/ruff format .

## clean: remove virtualenv and cached files
clean:
	rm -rf $(VENV) __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
