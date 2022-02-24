#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

PYTHON ?= python3
PYTHON_EXE = python
PIP = pip3
VENV_DIRECTORY = venv
PROJECT_DIRECTORY = ees_sharepoint
TEST_DIRECTORY = tests
COVERAGE_THRESHOLD = 0 # In percents, so 50 = 50%
EXEC_DIR = bin
CMD_UPDATE = touch

.DEFAULT_GOAL = help

ifeq ($(OS),Windows_NT)
    detected_OS := Windows
    EXEC_DIR := Scripts
	CMD_UPDATE := type nul >
endif

help:
	@echo "make install_locally - install the project into virtual environment for development purposes"
	@echo "make install_package - install the project for the user"
	@echo "make uninstall_package - uninstall the project for the user"
	@echo "make test - run the tests for the project"
	@echo "make cover - check test coverage for the project"
	@echo "make lint - run linter against the project"
	@echo "make clean - remove venv and other temporary files from the project"
	@echo "make test_connectivity - test connectivity to Sharepoint and Enterprise Search"

.venv_init:
	${PIP} install virtualenv
	${PYTHON} -m venv ${VENV_DIRECTORY}
	${CMD_UPDATE} .venv_init

.installed: .venv_init
	${VENV_DIRECTORY}/${EXEC_DIR}/${PIP} install -U pip
	${VENV_DIRECTORY}/${EXEC_DIR}/${PIP} install -r requirements.txt
	${CMD_UPDATE} .installed

# install_locally can be used to test the implementation after the changes were made to the module
# #{VENV_DIRECTORY}/bin will contain a file with name ${PROJECT_DIRECTORY} that is the main
# executable.
install_locally: .installed .venv_init
	${VENV_DIRECTORY}/${EXEC_DIR}/${PIP} install .

test: .installed .venv_init
	${VENV_DIRECTORY}/${EXEC_DIR}/${PYTHON_EXE} -m pytest ${TEST_DIRECTORY}/ --suppress-no-test-exit-code

cover: .installed .venv_init
	${VENV_DIRECTORY}/${EXEC_DIR}/${PYTHON_EXE} -m pytest --cov ${PROJECT_DIRECTORY} --cov-fail-under=${COVERAGE_THRESHOLD} ${TEST_DIRECTORY}/ --suppress-no-test-exit-code

lint: .installed .venv_init
	${VENV_DIRECTORY}/${EXEC_DIR}/flake8 ${PROJECT_DIRECTORY}

test_connectivity: .installed .venv_init
	${VENV_DIRECTORY}/${EXEC_DIR}/pytest ${PROJECT_DIRECTORY}/test_connectivity.py

install_package: .installed
	${PIP} install --user .

uninstall_package:
	${PIP} uninstall ${PROJECT_DIRECTORY} -y


clean:
ifeq ($(detected_OS),Windows)
	if exist venv rd /s /Q venv 2>nul
	if exist build rd /s /Q build 2>nul
	if exist ${PROJECT_DIRECTORY}.egg-info rd /s /Q ${PROJECT_DIRECTORY}.egg-info 2>nul
	if exist .pytest_cache rd /s /Q .pytest_cache 2>nul
	if exist .coverage del /s /Q .coverage 2>nul
	if exist .installed del /Q .installed 2>nul
	if exist .venv_init del /Q .venv_init 2>nul
else
	rm -rf venv
	rm -rf build
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -f .coverage
	rm -f .installed
	rm -f .venv_init
endif
