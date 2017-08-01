E2E NLG Challenge Evaluation metrics
====================================

The metrics used for the challenge include:
* BLEU + NIST from [MT-Eval](#mt-eval),
* METEOR, ROUGE-L, CIDEr from the [MSCOCO Caption evaluation scripts](#microsoft-coco-caption-evaluation-scripts).

So far, both evaluation scripts need to be run separately. A more convenient way of running the scripts will appear soon.

MT-Eval
-------

We used the NIST MT-Eval v13a script adapted for significance tests, from 
<http://www.cs.cmu.edu/~ark/MT/>.
We adapted the script to allow a variable number of references.

### Requirements ###
- Perl 5.8.8 or higher
- [XML::Twig](http://search.cpan.org/~mirod/XML-Twig-3.49/Twig.pm) CPAN module

### Usage ###

1. __Convert the sources, references, and your system outputs into the `.sgm` format__

   The `.sgm` files with the maximum number of references available for any instance.
   If there are less references available for some instances, use empty references instead. 
   These will be ignored by the script.

   The `.sgm` files can be created using the [txt2sgm.py](https://github.com/UFAL-DSG/tgen/blob/master/util/txt2sgm.py)
   script from the [TGen](https://github.com/UFAL-DSG/tgen) repository. 
   
   The script assumes plain text files with one instance per line on the input, as created 
   by the initial [data conversion for TGen](https://github.com/UFAL-DSG/tgen/blob/master/e2e-challenge/README.md).
   Multiple references for the same meaning representation (MR) should be separated by empty 
   lines in the reference file (not source or system output file, where one output per MR is 
   assumed).

```
~/tgen/util/txt2sgm.py -n e2e -l en -t ref -s manual -m devel-conc.txt devel-conc.sgm
~/tgen/util/txt2sgm.py -n e2e -l en -t src -s source devel-conc_das.txt devel-conc_das.sgm
~/tgen/util/txt2sgm.py -n e2e -l en -t test -s system outputs.txt outputs.sgm
```

2. __Run the MT-Eval script__

   This prints out BLEU and NIST on the standard output.

```
./mteval/mteval-v13a-sig.pl -r devel-conc.sgm -s devel-conc_das.sgm -t outputs.sgm -f mteval.log
```


Microsoft COCO Caption Evaluation scripts
-----------------------------------------

These provide a different variant of BLEU (which is not used for evaluation in the E2E challenge), 
METEOR, ROUGE-L, CIDER.

### Requirements ###

- Java 1.8,
- Python 2.7 with [matplotlib](https://pypi.python.org/pypi/matplotlib) and [scikit-image](https://pypi.python.org/pypi/scikit-image) packages. These can be installed using `pip`:

```
pip install -r requirements.txt
```

### Usage ###

The main entry point is [measure_scores.py](measure_scores.py). The script assumes one instance
per line for your system outputs and one entry per line, multiple references for the same instance
separated by empty lines for the references (see 
[TGen data conversion](https://github.com/UFAL-DSG/tgen/blob/master/e2e-challenge/README.md)).

```
./measure_scores.py devel-conc.txt outputs.txt
```


References
----------

- [Microsoft COCO Captions: Data Collection and Evaluation Server](http://arxiv.org/abs/1504.00325)
- PTBTokenizer: We use the [Stanford Tokenizer](http://nlp.stanford.edu/software/tokenizer.shtml) which is included in [Stanford CoreNLP 3.4.1](http://nlp.stanford.edu/software/corenlp.shtml).
- BLEU: [BLEU: a Method for Automatic Evaluation of Machine Translation](http://www.aclweb.org/anthology/P02-1040.pdf)
- NIST: [Automatic Evaluation of Machine Translation Quality Using N-gram Co-Occurrence Statistics](http://www.mt-archive.info/HLT-2002-Doddington.pdf)
- Meteor: [Project page](http://www.cs.cmu.edu/~alavie/METEOR/) with related publications. We use the latest version (1.5) of the [Code](https://github.com/mjdenkowski/meteor). Changes have been made to the source code to properly aggreate the statistics for the entire corpus.
- Rouge-L: [ROUGE: A Package for Automatic Evaluation of Summaries](http://anthology.aclweb.org/W/W04/W04-1013.pdf)
- CIDEr: [CIDEr: Consensus-based Image Description Evaluation](http://arxiv.org/pdf/1411.5726.pdf)

Acknowledgements
----------------
Original developers of the MSCOCO evaluation scripts:

Xinlei Chen, Hao Fang, Tsung-Yi Lin, Ramakrishna Vedantam, David Chiang, Michael Denkowski, Alexander Rush
