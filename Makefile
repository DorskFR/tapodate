APP ?= tapodate
TESTS ?= ./tests
PYTHON ?= ./.venv/bin/python
REPOSITORY_URL ?= ghcr.io/dorskfr/$(subst _,-,$(APP))
IMAGE_TAG ?= $(shell grep '^version = ' pyproject.toml | sed -E 's/version = "(.*)"/\1/')

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} \;
	find . -type d -name .cache -prune -exec rm -rf {} \;
	find . -type d -name .mypy_cache -prune -exec rm -rf {} \;
	find . -type d -name .pytest_cache -prune -exec rm -rf {} \;
	find . -type d -name .ruff_cache -prune -exec rm -rf {} \;
	find . -type d -name venv -prune -exec rm -rf {} \;

setup/pip:
	python -m venv .venv
	./.venv/bin/python -m pip install -r requirements-dev.lock

lint:
	$(PYTHON) -m ruff check ./$(APP) $(TESTS)
	$(PYTHON) -m ruff format --check ./$(APP) $(TESTS)
	$(PYTHON) -m mypy --cache-dir .cache/mypy_cache ./$(APP) $(TESTS)

lint/fix:
	$(PYTHON) -m ruff check --fix-only ./$(APP) $(TESTS)
	$(PYTHON) -m ruff format ./$(APP) $(TESTS)

run:
	$(PYTHON) -m $(APP)

setup:
	rye sync

test:
	$(PYTHON) -m pytest --rootdir=. -o cache_dir=.cache/pytest_cache $(TESTS) -s -x -v $(options)


docker/build:
	docker build \
		--platform linux/amd64 \
		--build-arg PROJECT_NAME=$(APP) \
		--build-arg VERSION=$(IMAGE_TAG) \
		--build-arg PYTHON_VERSION=$(shell cat .python-version | awk -F. '{print $$1"."$$2}') \
		-t $(REPOSITORY_URL):$(IMAGE_TAG) \
		-t $(REPOSITORY_URL):latest \
		.

docker/push:
	docker push  $(REPOSITORY_URL):$(IMAGE_TAG)

docker/run:
	docker run --rm -it --name $(APP) $(REPOSITORY_URL):$(IMAGE_TAG)

.PHONY: $(shell grep --no-filename -E '^([a-zA-Z_-]|\/)+:' $(MAKEFILE_LIST) | sed 's/:.*//')
