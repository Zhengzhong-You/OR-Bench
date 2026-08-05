LATEXMK ?= latexmk
PDFDIR := output/pdf

.PHONY: pdf-all pdf-ctirp pdf-pcl clean

pdf-all: pdf-ctirp pdf-pcl

$(PDFDIR):
	mkdir -p $(PDFDIR)

pdf-ctirp: | $(PDFDIR)
	cd problems/01_event_ordered_continuous_time_replenishment && $(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=../../$(PDFDIR) event_ordered_continuous_time_replenishment.tex

pdf-pcl: | $(PDFDIR)
	cd problems/02_pcl_assortment && $(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=../../$(PDFDIR) pcl_assortment.tex

clean:
	cd problems/01_event_ordered_continuous_time_replenishment && $(LATEXMK) -C -outdir=../../$(PDFDIR) event_ordered_continuous_time_replenishment.tex
	cd problems/02_pcl_assortment && $(LATEXMK) -C -outdir=../../$(PDFDIR) pcl_assortment.tex
