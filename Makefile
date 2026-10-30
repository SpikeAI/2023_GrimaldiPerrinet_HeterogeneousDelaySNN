default: all
all: render pdf html git
################################################
# CODE
################################################

J=jupyter nbconvert --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=0 --allow-errors --execute
JM=$(J) --to markdown  --stdout # for dev
JN=$(J) --to notebook  --inplace # for the final touch

#################@#################@#################@#################
#################@#################@#################@#################
install:
	pip install -r requirements.txt
	
run:
	$(JM) FastMotionDetection.ipynb

render: 
	$(JN) FastMotionDetection.ipynb

################################################
# DOCUMENTATION (GitHub Pages)
################################################
# The online documentation is the notebook rendered as a single page, served by
# GitHub Pages at
# https://spikeai.github.io/2023_GrimaldiPerrinet_HeterogeneousDelaySNN/
# It reuses the outputs of `make render`, so nothing is recomputed here.
# `html` builds build/html/index.html, `docs` publishes it on the gh-pages branch.
BUILD = build/html
DOC = $(BUILD)/index.html
# nbconvert without --execute: the page reuses the outputs left by `make render`.
JH = jupyter nbconvert --to html
PY = python3

html: $(DOC)

$(DOC): FastMotionDetection.ipynb build_docs.py
	$(JH) $< --output index.html --output-dir $(@D)
	$(PY) build_docs.py $@

docs: $(DOC)
	$(PY) build_docs.py $< --publish

docs-check:
	$(PY) build_docs.py --check --online

################################################
# MANUSCRIPT
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


GROUPID = 4776796
zotero_fetch_bib:
	# limited to 100 items :-( 
	wget "https://api.zotero.org/groups/4776796/items?format=bibtex&limit=100&start=0" -O FastMotionDetection.bib
	# curl https://api.zotero.org/groups/$(GROUPID)/items?format=bibtex > FastMotionDetection.bib


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
