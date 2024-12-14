[![CC BY 4.0][cc-by-shield]][cc-by]
# ECCO_Drama
A collection of 288 English-language plays sourced from ECCO-TCP.

## Project Description
This project resulted out of the need to create a collection of 18<sup>th</sup>-century English-language plays. Instead of proceeding from manually encoding files, I thought it quicker and more beneficial for the community to improve upon the mostly automatically encoded files that resulted from the Eighteenth Century Collection Online-Text Creation Partnership ([ECCO-TCP](http://www.lib.umich.edu/tcp/ecco)). I have examined all the files containing dramatic components (in the form of stage directions), keeping only actual plays. In a second step, motivated by my own research interests, I have excluded everything not corresponding with my myopic understanding of full, spoken, dramatic works, i.e., the following genre were removed: operas, musical farces/plays/dramas, burlettas, oratorios, dramatic entertainments, masques, pantomimes, interludes, etc. What remains is a collection of comedies, tragedies, dramas, farces, plays, mock-tragedies, tragicomedies, etc. This leaves us with 288 files, of which 3 are translations from French and 12 are at present unfixable.

## Editorial Process
The files were heavily reworked and proofread. On the most basic level, I have split anthologies into separate files (keeping the original ID plus a hyphenated number corresponding to the position of the play in the original file, e.g., the first drama in K041482.000 is K041482.000-1) and have changed the entire XML to be valid TEI P5.

More ambitiously, the following changes were introduces systematically (and at points serendipitously):
- Stage directions have been divided from scene heading.
- Stage directions have been divided from speech prefixes.
- Settings have been encoded with set.
- Missing scene divisions have been added along scenery changes.
- Dialog not assigned to a speaker has been assigned.
- Mistakes found in errata lists have been corrected (aside from one cryptic one in K100402).
- Gaps (i.e., illegibilities stemming from the OCR process)[^1] have been looked up and filled. To achieve this, I have employed the original edition used by ECCO-TCP. Whenever a word was truly illegible, I have opted to consult other textual witnesses.
- Duplicate pages have been removed.
- Prologues and Epilogues have been moved to the front or back matter, whenever they were erroneously added to the start or end of the body.
- Lines in verse plays that were erroneously encoded as paragraphs have been fixed (though not exhaustively).
- Songs have been encoded coherently with lg[@type="song"] (where they were previously encoded as songs in a different manner).
- Superscript, previously as \<sup>, has been replaced with span[@rend="sup"].
- Missing page numbers have been added.
- The encoding for letters appearing in the dialog has been simplified.

Furthermore, I have conducted some broad proofreading efforts. This includes frequent OCR mistakes like the confusion between ſ (long s), f and t; n and h; vv and w, etc. Additionally, I have checked for the 10 least common occurring bigrams[^2] as well as the 7 impossible bigrams in English[^3].

## Missing changes: 
Aside from the fact that the entirely collection would benefit from being proofread thoroughly from digital cover to digital cover, the following changes are still outstanding:
- Front and back matter as well as footnotes have been treated somewhat superficially. I have corrected obvious errors (and settings), but have not engaged with any subtleties.
- Dramatis personae are merely lists instead of castList elements.
- Somewhat consequently, characters have not been assigning @xml:id and @who has not been assigned to speeches.
- The foreign quotes from non-Latin script (e.g., from Sophocles' Electra in K010938) have not been added due to my linguistic limitations, but are indicated with \<gap reason="foreign"/>. Maybe someone more apt in Greek will resolve this issue.
- The documents are sprinkled with the symbol ▪, which sometimes indicates an actual punctuation (mostly, dots, commas, and semicolons) and quite often merely indicates schmutz on the original print. As there are 549 occurrences of this symbol in 148 files, I have not found the time nor motivation to correct them. However, I have also not deleted them, as this will make proofreading for missing punctuation easier in the future.

### Unfixable files
Some files, currently in the folder "unfixable," could not be finished entirely because of one of three problems:
1. Some files have hundreds of gaps and are simply **too broken**. This might make it more feasible to encoding them from scratch instead of fixing the existing versions: K02153, K032305, K032321, K039425, K046880, K047435
2. Some files have **missing pages**, which would need to be encoded from scratch. Up until now, this is beyond the scope I had set for this project: K046628, K051011, K102974,K120041
3. For one file, only the version used for the original ECCO-TCP version exists. Due to the degradation of the original print and the poor quality of the scan, proofreading the gaps is impossible: K000958

## A word of caution
While I have proceeded with the greatest of care in correcting the files, normalizing markup, and proofreading for errors, the versions presented here are by no means perfect. From my experience working with the collection, erroneous words stemming from the OCR process seem to appear infrequently, but they do appear and this should be taken into account. I do not wish to deter anyone from using this collection, merely to state that this is not a pristine critical edition. Proceed at your own risk and scale your project to the quality of the data. 


This work is licensed under a
[Creative Commons Attribution 4.0 International License][cc-by].

[![CC BY 4.0][cc-by-image]][cc-by]

[cc-by]: http://creativecommons.org/licenses/by/4.0/
[cc-by-image]: https://i.creativecommons.org/l/by/4.0/88x31.png
[cc-by-shield]: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg


[^1]: As ECCO-TCP explain: "After proofreading, the encoding was enhanced and/or corrected and characters marked as illegible were corrected where possible up to a limit of 100 instances per text. Any remaining illegibles were encoded as \<gap>s. Understanding these processes should make clear that, while the overall quality of TCP data is very good, some errors will remain and some readable characters will be marked as illegible. Users should bear in mind that in all likelihood such instances will never have been looked at by a TCP editor."
[^2]: https://www.petercollingridge.co.uk/blog/language/analysing-english/bigrams/
[^3]: http://norvig.com/mayzner.html
  Although, WZ is not impossible in 18<sup>th</sup>-century English (I might be rowz'd to say drowzily) and Mr. Crowquill from Hannah Cowley's *The belle's stratagem* might object to the assumed impossibility of WQ.
