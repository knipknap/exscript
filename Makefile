NAME=exscript
VERSION=`python setup.py --version | sed s/^v//`
PREFIX=/usr/local/
BIN_DIR=$(PREFIX)/bin
LIB_DIR=$(PREFIX)/lib
SITE_DIR=$(LIB_DIR)/python/site-packages
DISTDIR=/pub/code/releases/$(NAME)

###################################################################
# Standard targets.
###################################################################
.PHONY : clean
clean:
	find . -name "*.pyc" -o -name "*.pyo" | xargs -n1 rm -f
	rm -Rf build src/*.egg-info
	cd doc; make clean

.PHONY : dist-clean
dist-clean: clean
	rm -Rf dist

.PHONY : doc
doc:
	cd doc; make

install:
	mkdir -p $(SITE_DIR)
	./version.sh
	export PYTHONPATH=$(SITE_DIR):$(PYTHONPATH); \
	python setup.py install --prefix $(PREFIX) \
	                        --install-scripts $(BIN_DIR) \
	                        --install-lib $(SITE_DIR)
	./version.sh --reset

uninstall:
	# Sorry, Python's distutils support no such action yet.

.PHONY : tests
tests:
	cd tests/Exscript/; ./run_suite.py 1

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

.PHONY : doc-publish
doc-publish:
	cd doc; make publish
