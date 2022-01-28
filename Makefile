#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

PYTHON = python3
PIP = pip3
VENV_DIRECTORY = venv
PROJECT_DIRECTORY = ees_sharepoint

.DEFAULT_GOAL = help

help:
	@echo "make setup - set up the project locally"
	@echo "make test - run the tests for the project"
	@echo "make cover - check test coverage for the project"
	@echo "make lint - run linter against the project"
	@echo "make clean - remove venv directory from the project"

.venv_init:
	${PIP} install virtualenv
	${PYTHON} -m venv ${VENV_DIRECTORY}
	touch .venv_init

.installed: .venv_init
	${VENV_DIRECTORY}/bin/${PIP} install -r requirements.txt
	touch .installed

install_locally: .installed .venv_init
	${VENV_DIRECTORY}/bin/${PIP} install .

test: .installed .venv_init
	${VENV_DIRECTORY}/bin/${PYTHON} -m pytest

cover: .installed .venv_init
	${VENV_DIRECTORY}/bin/pytest --cov ${PROJECT_DIRECTORY} --cov-fail-under=80 tests

lint: .installed
	${VENV_DIRECTORY}/bin/flake8 ${PROJECT_DIRECTORY}

clean:
	rm -rf venv
	rm -rf build
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -f .coverage
	rm -f .installed
	rm -f .venv_init
