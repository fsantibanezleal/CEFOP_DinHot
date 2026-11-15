- Adopted CAOS_PRODUCT_TEMPLATE 0.15.011 and 0.15.012 through `template_adopt.py`. The manuscript content check measures the abstract
  as it prints (150 to 250 words for a paper, 200 to 300 for the technical report), so it refuses the three papers whose abstracts ran
  over at 0.02.003 until their revisions shorten them. The readiness admission tests pin the generation environment's root, and the
  template's browser checks launch without a proxy. The one conflict, the repository validation rows RP-018 and RP-026, keeps DinHot's
  rows and adds the template's new admission test to RP-018.
