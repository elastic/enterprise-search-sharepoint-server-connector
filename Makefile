PYTHON = python3
PIP = pip3
VENV_DIRECTORY = venv

.DEFAULT_GOAL = help

help:
	@echo "make venv_init - set up and activate venv for the project"
	@echo "make setup - set up the project locally"
	@echo "make test - run the tests for the project"
	@echo "make clean - remove venv directory from the project"

venv_init:
	${PYTHON} -m venv ${VENV_DIRECTORY}

setup:
	${PIP} install -r requirements.txt

install_locally:
	${VENV_DIRECTORY}/bin/${PIP} install .

test:
	${PYTHON} -m pytest

lint:
	pylint ees_sharepoint

clean:
	rm -rf venv
	rm -rf build
	rm -rf *.egg-info
