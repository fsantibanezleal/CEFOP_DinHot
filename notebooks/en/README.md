# Notebooks, English

The index of the English tree. Topics run from simple to complex; inside a topic the reading order is the notebook
number and the level never goes down. The Spanish counterpart of every notebook is at the same path under
[`../es/`](../es/README.md). How to run them is in [`../README.md`](../README.md).

Levels: 1 fundamentals, 2 the method in practice, 3 state of the art, 4 beyond the state of the art.

Each notebook is a worked lesson on one question: it states the question in its first cell, runs the engine step by step on
the example's cases, shows what it finds in figures, and answers the question in its Results with numbers it computed
([`docs/guides/08_notebooks.md`](../../docs/guides/08_notebooks.md)).

## Topics

A topic without a level 3 notebook says why on its row.

| Topic | Needs | Level 3 |
|---|---|---|
| [01-getting-started](01-getting-started/) | none, this is the entry topic | [03-a-higher-order-solver](01-getting-started/03-a-higher-order-solver.ipynb) |
| [02-threshold-and-final-size](02-threshold-and-final-size/) | topic 01-getting-started | No level 3: the research basis names no newer method for the threshold or the final size, and the example's one state-of-the-art comparison, the higher-order solver, is in topic 01 |

## Notebooks

| Notebook | Level | The question it answers |
|---|---|---|
| [01-getting-started/01-the-problem-and-the-data.ipynb](01-getting-started/01-the-problem-and-the-data.ipynb) | 1 | how a town of 100000 people runs through an epidemic day by day: the peak, its day and the final toll, and how they move when the first cases or the infectious period change |
| [01-getting-started/02-the-method-step-by-step.ipynb](01-getting-started/02-the-method-step-by-step.ipynb) | 2 | how wrong the engine's Forward Euler step is, against the exact final size and peak, for which cases it matters, and what extrapolation recovers |
| [01-getting-started/03-a-higher-order-solver.ipynb](01-getting-started/03-a-higher-order-solver.ipynb) | 3 | how SciPy's RK45 compares with the engine on the same cases, by error against the step and against the cost |
| [02-threshold-and-final-size/01-the-threshold.ipynb](02-threshold-and-final-size/01-the-threshold.ipynb) | 1 | for which contact and recovery rates an outbreak takes off, how it looks just above the threshold, and what immune share stops it |
| [02-threshold-and-final-size/02-the-final-size.ipynb](02-threshold-and-final-size/02-the-final-size.ipynb) | 2 | what share an outbreak infects in the end, why it ignores the speed of the course, and where the engine's run does not reach it |

## Beyond the state of the art

None claimed: the example is a teaching model, so it has no level 4 notebook. A product that claims a component beyond
the state of the art lists it in its SDD and covers it with a level 4 notebook in each language
([`docs/guides/08_notebooks.md`](../../docs/guides/08_notebooks.md)).
