PYTHON ?= python3
HELM ?= helm
CHARTS := $(sort $(dir $(wildcard charts/*/Chart.yaml)))
APPLICATIONS := $(filter-out charts/octelium-common/,$(CHARTS))
.DEFAULT_GOAL := test

.PHONY: dependencies lint test package clean

dependencies:
	@for chart in $(APPLICATIONS); do $(HELM) dependency build --skip-refresh "$$chart" || exit $$?; done

lint:
	$(PYTHON) -m ruff check ci tests
	$(PYTHON) -m ruff format --check ci tests
	$(PYTHON) -m ci.lint_charts

test:
	$(PYTHON) -m unittest discover -s tests -v

package:
	$(PYTHON) -m ci.package_charts $(if $(VERSION),--version "$(VERSION)")

clean:
	$(PYTHON) -c 'import shutil; shutil.rmtree("dist", ignore_errors=True)'
