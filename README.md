# Deutschlandticket Commute Analysis

Estimates how attractive public transport, and the Deutschlandticket, would be for
employees commuting to **Johnson & Johnson Medical GmbH, Robert-Koch-Strasse 1, 22851
Norderstedt**.

No real employee data is used. A synthetic workforce is generated around Hamburg, each
person's door-to-door transit commute is computed, and an adoption score is estimated.

## What it does
1. Generates synthetic employees around Hamburg and surrounding towns.
2. Computes each door-to-door transit commute using a live HVV routing service, with a
   distance-based fallback if a call fails.
3. Groups commutes into 0-30, 30-45, 45-60 and 60+ minute bands.
4. Scores Deutschlandticket adoption with a transparent weighted model.
5. Produces a summary and an interactive map.

## Method notes
- **Routing:** live journeys from `v6.db.transport.rest`, a free HAFAS wrapper over
  Deutsche Bahn data that covers HVV. No API key is needed. Results are cached to
  `data/cache/`. If a request fails, a distance-based estimate is used instead. The
  `source` column records which was used per employee.
- **Adoption score:** a stated, interpretable model, not trained on real behaviour. It
  combines commute time, transfers, walk to the first stop, car ownership and money saved
  against driving, passed through a logistic function. All weights and cost assumptions
  are in `src/config.py`.
- **Deutschlandticket price:** 63 EUR per month, the rate from January 2026.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
Open `notebook.ipynb` and run all cells, or:
```bash
jupyter notebook notebook.ipynb
```
The routing step needs internet access. To test the flow offline first, set
`USE_API = False` in the commute cell to use estimates only. `N` sets the number of
synthetic employees.

After a full run, `outputs/` contains `employees.csv`, `summary.md` and
`commute_map.html`. Commit these so the results are visible without rerunning.

## Structure
```
notebook.ipynb        Main analysis, runs the full pipeline
src/config.py         Workplace, bins, weights, cost assumptions
src/synthetic.py      Synthetic employee generation
src/routing.py        Live routing, caching, fallback estimator
src/scoring.py        Binning, savings, adoption score
src/mapping.py        Interactive Folium map
outputs/              Generated results
```