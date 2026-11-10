"""The respondent prompt for the 2026Q3 corpus: the locked question plus a fixed no-internet line.

User rule (2026-10-24): every prompt sent to a respondent model carries a line telling it not to use the internet,
so models don't fetch anything from the web. The line is a harness instruction, not information about the finding:
the parallel-true and minimality audits apply to the question only, and the line is exempt like the fixed ending.

Fields (corpus, prompts_2026Q3.json, corpus_abstracts_2026Q3.json):
  question       the locked, audited question
  model_prompt   the exact text a respondent receives = respondent_prompt(question)
"""

NO_INTERNET_LINE = 'Do not use the internet.'


def respondent_prompt(question):
    q = question.strip()
    assert NO_INTERNET_LINE not in q, 'question already carries the no-internet line'
    return f'{q}\n\n{NO_INTERNET_LINE}'
