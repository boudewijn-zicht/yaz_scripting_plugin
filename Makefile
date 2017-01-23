init:
	pip3 install -r requirements.txt

test:
	nosetests --with-coverage --cover-html --cover-package yaz_scripting_plugin

.PHONY: init test
