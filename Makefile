################################################
SRC = Grimaldi-etal-BiolCybernetics
SLUG = grimaldi-23-bc
# SRC_rev = Pasturel_etal2019
DIR_rev = revision_0
SRC_rev = $(DIR_rev)/$(SRC)
#LATEXMK = latexmk -pdf -pdflatex=lualatex
LATEXMK = latexmk -pdf
BIBTEX = bibtex
################################################
default: pdf git
pdf: $(SRC).pdf
diff: $(SRC)_trackedchanges.pdf
################################################
LATEXMK = latexmk -bibtex -pdf
#  -pdflatex=pdflatex
################################################


$(SRC).pdf: $(SRC).tex FastMotionDetection.bib
	$(LATEXMK) $(SRC).tex
	
# post-production
$(SRC)_trackedchanges.tex: $(SRC).tex FastMotionDetection.bib $(SRC_rev).tex
	latexdiff --flatten --graphics-markup=both $(SRC_rev).tex $(SRC).tex > $(SRC)_trackedchanges.tex

response_to_reviewers.pdf: response_to_reviewers.tex $(SRC).tex $(SRC).bib
	$(LATEXMK) response_to_reviewers.tex

touch:
	touch *.tex

# blog:
# 	cp Grimaldi-etal-BiolCybernetics.pdf /Users/laurentperrinet/metagit/blog/hugo_academic/content/publication/grimaldi-23-bc/grimaldi-23-bc.pdf
blog:
	cp $(SRC).pdf ~/quantic/blog/hugo_academic/content/publication/$(SLUG)/$(SLUG).pdf
git:
	git pull
	git commit -am'Another pass'
	git push

# macros
%.pdf: %.tex
	$(LATEXMK) $<

%.pdf: %.svg
	$(INKSCAPE) --without-gui $< --export-pdf=$@

%.png: %.svg
	$(INKSCAPE) --without-gui $< --export-png=$@ -d 450

# cleaning macro
clean:
	rm -f *.dvi *.fls *.ilg *.ind *idx *.bcf *.run.xml *.dvi *.ps *.out *.log *.aux *.bbl *.blg  *.fdb_latexmk *.snm *.nav *.toc *.info *.synctex.gz* $(SRC).pdf  *-nup.pdf
