LATEXMK ?= latexmk
PDFDIR := output/pdf

.PHONY: pdf-all pdf-snd pdf-ctirp pdf-pcl clean

pdf-all: pdf-snd pdf-ctirp pdf-pcl

$(PDFDIR):
	mkdir -p $(PDFDIR)

pdf-snd: | $(PDFDIR)
	cd problems/01_cyclic_crossdock_service_network_design && TEXINPUTS=../../latex: $(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=../../$(PDFDIR) cyclic_crossdock_service_network_design.tex

pdf-ctirp: | $(PDFDIR)
	cd problems/02_event_ordered_continuous_time_replenishment && TEXINPUTS=../../latex: $(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=../../$(PDFDIR) event_ordered_continuous_time_replenishment.tex

pdf-pcl: | $(PDFDIR)
	cd problems/03_pcl_assortment && TEXINPUTS=../../latex: $(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=../../$(PDFDIR) pcl_assortment.tex

clean:
	cd problems/01_cyclic_crossdock_service_network_design && $(LATEXMK) -C -outdir=../../$(PDFDIR) cyclic_crossdock_service_network_design.tex
	cd problems/02_event_ordered_continuous_time_replenishment && $(LATEXMK) -C -outdir=../../$(PDFDIR) event_ordered_continuous_time_replenishment.tex
	cd problems/03_pcl_assortment && $(LATEXMK) -C -outdir=../../$(PDFDIR) pcl_assortment.tex
