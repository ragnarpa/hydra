sdist:
	python3 setup.py sdist

install: clean sdist
	pip install dist/hydra-ctl-*

uninstall:
	pip uninstall hydra-ctl

test:
	python3 setup.py test

clean:
	find $(shell pwd) -name "__pycache__" -type d | xargs rm -fr
	rm -fr .eggs .pytest_cache dist src/hydra_ctl.egg-info
