# Extraction protocol

*Plain language: these are the rules for reading a number out of a paper and typing it into the benchmark. Following the same rules every time is what makes results from different labs comparable. Anyone, including you in two years, should be able to re-extract a paper and get the same row.*

**Status: v1.0.0 (October 2026). Judgment calls below were confirmed by the maintainer; see the decision record at the end.**

## 1. Which papers are in scope

A paper is included when all of these hold:

1. It reports **direct (non-oxidative) propane dehydrogenation**: C3H8 to C3H6 + H2 with no oxidant (O2, CO2, N2O, S-containing oxidants) in the feed. Oxidative and CO2-assisted dehydrogenation are excluded because the equilibrium ceiling below does not apply to them.
2. It reports **propane conversion** at a stated temperature for at least one catalyst.
3. The feed composition can be determined (propane fraction, any H2 co-feed, diluent).
4. It is a peer-reviewed article or a preprint with a DOI.

Excluded: purely computational studies, membrane reactors and chemical-looping reactors (their ceiling differs; logged in `docs/NEXT_STEPS.md` for a later layer), and results reported only as rates with no conversion.

Searching: Web of Science or Scopus if available, otherwise Google Scholar and OpenAlex, query `"propane dehydrogenation" AND (catalyst)`, plus the reference lists of the major reviews. Each search string, date, and hit count is logged in `data/extraction/search_log.csv` so the selection can be repeated.

## 2. Units and conventions

| Quantity | Enter as | Notes |
|---|---|---|
| Temperature | °C | Convert K by subtracting 273.15. |
| Pressure | bar, absolute | "Atmospheric" or "ambient" with no number: 1.01325, and `pressure_assumed` = TRUE. Gauge pressures: add 1.01325. |
| Feed | mole fractions | Volume ratios of ideal gases equal mole fractions. "C3H8:H2:N2 = 1:1:8" is 0.1 / 0.1 / N2. |
| WHSV | g propane per g catalyst per hour | If the paper's WHSV is on total feed, convert to propane basis and note it. |
| Conversion, selectivity, yield | percent | Fractions times 100. |
| Time on stream | hours | Minutes divided by 60. |

## 3. Where a value comes from

Use the most precise location available, in this order: a table in the main text, a table in the supplementary information, a number stated in the text, a value read from a figure.

- **Table or text values:** copy exactly. Record `location` (for example `Table 2, row 4` or `p. 6, para 2`).
- **Figure values:** digitize with WebPlotDigitizer (free, https://automeris.io). Export the read coordinates as CSV to `data/extraction/digitization/<catalyst_id>_<figure>.csv` so anyone can check them (see section 7 for why we do not keep the image). Set `value_origin` to `figure_digitized`. Round to 0.5 percentage points; reading precision is rarely better.
- Never estimate a value the paper does not show. A missing value stays blank.

## 4. Which points to extract

- **Initial activity:** the first reported time-on-stream point for every catalyst and condition.
- **Stability tests:** first point, last point, and enough points between to show the shape (about one per 10% of the run). Give all points from one continuous test the same `run_label`.
- **Temperature series:** every reported temperature.
- **Regeneration cycles:** first point of each cycle, with `regeneration_cycle`.
- **Reference catalysts** (for example commercial Pt-Sn or a lab's own baseline): always extract. They are what lets labs be compared to each other.

## 5. The judgment calls

These decide whether two reported numbers mean the same thing. The extractor records what the paper says; the comparison layer decides how to use it.

1. **Temperature basis.** Record what the temperature measures (`setpoint`, `bed_thermocouple`, `pyrometer`, and so on). This matters most for induction, microwave, radio-frequency, and Joule heating, where the catalyst surface can be much hotter or cooler than the reported number. If the paper does not say, use `unreported`.
2. **Conversion basis.** `carbon_balance_products` (conversion computed from products detected) and `propane_consumption` (from propane disappearing) differ when carbon balance is poor, because coke counts as conversion only in the second.
3. **Selectivity basis.** Carbon basis versus molar basis; most PDH papers use carbon basis.
4. **Deactivation constant.** Copy the paper's own kd and its formula into `kd_definition`. The pipeline separately recomputes one common kd from the first and last points of each run, so values from different papers can be compared. 
5. **Above the ceiling.** If a reported conversion is above the equilibrium limit, do not change it. Extract it as printed. The pipeline flags it, and the flag is part of the benchmark's value.

## 6. Recording a paper, step by step

1. Add the paper to `sources.csv`. Next free `source_id` (S0001, S0002, ...).
2. Add each catalyst to `catalysts.csv` as `S0001-C01`, `S0001-C02`, ... using the paper's own name in `label_in_paper`.
3. Add each test point to `measurements.csv` as `S0001-C01-M01`, ...
4. Put anything odd in `extractor_flags` (for example `temperature_ambiguous;feed_inferred_from_SI`).
5. Run `python code/03_build_and_qa.py`. Fix every ERROR. Read every WARN and FLAG against the paper.
6. A second person (or the maintainer on a later day) re-checks at least one row per paper against the PDF and fills `verified_by` and `verified_date`.

## 7. What we never copy

Numbers and facts are recorded with credit to the paper. Text, figures, and tables as images are never copied into the repository. WebPlotDigitizer project files (`.tar`) embed the figure image, so we keep only the coordinates-only `.csv` export, never the image.

## 8. Additions after the first batch (October 2026)

0. **Tools.** Extraction is done with software assistance (search, full-text download, AI-assisted reading of tables and text). Every entry is checked by the curator against the paper before release, and the automatic checks below run on every build.
1. **Finding papers.** `python code/00_literature.py search` queries Europe PMC for open-access full texts and logs the query in `search_log.csv`. `fetch PMC...` downloads full text for reading into `data/raw/literature/` (never published; only fingerprints go into `PROVENANCE.txt`). Every paper looked at is recorded in `screening_log.csv` as `included`, `deferred` (numbers only in figures or SI) or `excluded` (out of scope), with the reason.
2. **Comparison tables in papers.** Many papers include a table comparing their catalyst with earlier work. Only rows marked "this work" are entered. Rows citing other papers are never entered under the citing paper; the cited paper is added as its own source instead.
3. **Citations.** `first_author`, `year` and `journal` are filled from Crossref by `python tools/check_dois.py --fill`, never typed from memory. The same script reports any mismatch.
4. **Number tracing.** `python tools/trace_check.py` confirms every entered conversion and selectivity appears in the downloaded paper text. Values from papers not available as full text in Europe PMC are checked by hand against the publisher's version.
5. **Equilibrium values quoted by papers** go in `quoted_equilibria.csv`, with the conditions they refer to. The build compares each with this project's calculator.
6. **Approximate, ranged and bounded values.** "About 30%" is entered as 30 with `approximate_text_value`. "37 to 38%" is entered as the lower value with `range_reported_...`. "Over 29%" is entered as 29 with `conversion_is_lower_bound`.
7. **Feeds stated two ways.** When a paper's Methods and figure caption disagree on feed or flow, the one consistent with the stated space velocity is entered and the conflict is noted in `extractor_flags` and `notes`.
8. **Co-feeds.** Propylene co-feed goes in `y_C3H6_in` and enters the equilibrium. Trace sulfur co-feeds are noted but not modelled.

## 9. Decision record (confirmed by the maintainer, 19 October 2026)

| Decision | Choice |
|---|---|
| Scope | Direct (non-oxidative) PDH only. Oxidative, CO2-assisted, electric-field-assisted, membrane and chemical-looping studies excluded for now. |
| Temperature for electrified heating | Ceiling computed at the reported temperature in every case; `temperature_basis` records what was measured and rows with an unreported basis are warned. |
| Above-ceiling tolerance | Flag when conversion exceeds the ceiling by more than 2 percentage points. |
| Common deactivation constant | kd = [ln((1-Xf)/Xf) - ln((1-X0)/X0)] / t, first and last points of each labelled run. |
| Figure-reading precision | 0.5 percentage points. |
| Approximate and bounded values | Kept, flagged in `extractor_flags`. |
| Yield vs ceiling | v1.1 comparison layer reports both conversion and propylene yield against the ceiling. |
| Inconsistent units in a paper (S0005 kd) | Kept as printed, with a QA warning. |
| Space-velocity conversions | Converted to g propane per g catalyst per hour, marked `computed`. |
| Maintainer's own paper (S0017) | Included, with disclosure. Reactor pressure confirmed atmospheric. |
