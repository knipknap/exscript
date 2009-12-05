NAME=exscript
VERSION=`python setup.py --version`
PACKAGE=$(NAME)-$(VERSION)-1
PREFIX=/usr/local/
DISTDIR=/pub/code/releases/$(NAME)

###################################################################
# Standard targets.
###################################################################
clean:
	find . -name "*.pyc" -o -name "*.pyo" | xargs -n1 rm -f
	rm -Rf build src/*.egg-info

dist-clean: clean
	rm -Rf dist $(PACKAGE)*

doc:
	cd doc; make

install:
	python setup.py install --prefix $(PREFIX)

uninstall:
	# Sorry, Python's distutils support no such action yet.

tests:
	cd tests/$(NAME); \
		[ -e run_suite.* ] && ./run_suite.* || [ ! -e run_suite.* ]

###################################################################
# Package builders.
###################################################################
targz:
	./version.sh
	python setup.py sdist --formats gztar
	./version.sh --reset

tarbz:
	./version.sh
	python setup.py sdist --formats bztar
	./version.sh --reset

deb:
	./version.sh
	debuild -S -sa
	cd ..; sudo pbuilder build $(NAME)_$(VERSION)-0ubuntu1.dsc; cd -
	./version.sh --reset

dist: targz tarbz

###################################################################
# Publishers.
###################################################################
dist-publish: dist
	mkdir -p $(DISTDIR)/
	for i in dist/*; do \
		mv $$i $(DISTDIR)/`basename $$i | tr '[:upper:]' '[:lower:]'`; \
	done

doc-publish:
	cd doc; make publish
