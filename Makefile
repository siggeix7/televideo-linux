IMAGE ?= televideo-linux
TAG ?= latest
PORT ?= 8000
TMP_IMAGE ?= /tmp/$(IMAGE)-$(TAG).tar
PYTHON ?= python3

.PHONY: all build save run shell test clean

all: save

build:
	docker build -t $(IMAGE):$(TAG) .

save: build
	docker save $(IMAGE):$(TAG) -o $(TMP_IMAGE)
	@printf 'Container image saved in %s\n' "$(TMP_IMAGE)"

run: build
	docker run --rm -p $(PORT):8000 -v televideo-data:/data $(IMAGE):$(TAG)

shell: build
	docker run --rm -it -v televideo-data:/data $(IMAGE):$(TAG) manage shell

test:
	$(PYTHON) -m py_compile televideo
	$(PYTHON) web/manage.py check
	$(PYTHON) web/manage.py makemigrations --check --dry-run

clean:
	rm -f $(TMP_IMAGE)
