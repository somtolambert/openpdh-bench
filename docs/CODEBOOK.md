# Codebook

*Plain language: this explains every column in the benchmark, its unit, and whether it is required. It is generated automatically from `code/schema.py`, so do not edit it by hand.*

## sources.csv

| Column | Type | Unit | Required | Definition | Allowed |
|---|---|---|---|---|---|
| `source_id` | str |  | yes | Project ID for the paper, e.g. S0001. Never reused. |  |
| `doi` | str |  | yes | DOI of the paper, lower case, without https://doi.org/. |  |
| `first_author` | str |  | yes | Family name of the first author. |  |
| `year` | int |  | yes | Year of the version of record. | 1950 to 2030 |
| `journal` | str |  | yes | Journal or venue name as printed. |  |
| `open_access` | bool |  | yes | TRUE if the full text is free to read at the DOI. |  |
| `curated_by` | str |  | yes | Initials of the person responsible for the entry. |  |
| `extraction_date` | date |  | yes | ISO date the values were entered. |  |
| `verified_by` | str |  | no | Initials of the person who checked the values against the paper. Blank until checked. |  |
| `verified_date` | date |  | no | ISO date of the second check. |  |
| `notes` | str |  | no | Anything a reader needs about this paper as a whole. |  |

## catalysts.csv

| Column | Type | Unit | Required | Definition | Allowed |
|---|---|---|---|---|---|
| `catalyst_id` | str |  | yes | Project ID, e.g. S0001-C03 (source ID + catalyst number). |  |
| `source_id` | str |  | yes | Paper this catalyst comes from (links to sources.csv). |  |
| `label_in_paper` | str |  | yes | The catalyst's name exactly as the paper writes it, e.g. 'PtSn/Al2O3-0.5'. |  |
| `family` | enum |  | yes | Active-phase family, used for grouping. | `Pt`, `Pt-Sn`, `Pt-Ga`, `Pt-Zn`, `Pt-In`, `Pt-other`, `CrOx`, `GaOx`, `ZnOx`, `VOx`, `Co`, `Fe`, `Ni`, `In`, `Sn`, `Zr`, `Pt-Ge`, `carbon`, `zeolite_metal_free`, `other` |
| `active_elements` | str |  | yes | Active and promoter elements with nominal loading, semicolon-separated 'Element:wt%' pairs, e.g. 'Pt:0.5;Sn:1.0'. Use 'na' for loading not reported. |  |
| `loading_basis` | enum |  | yes | Whether loadings are nominal (as prepared) or measured (ICP, XRF, etc.). | `nominal`, `measured`, `unreported` |
| `support` | str |  | yes | Support material as written, e.g. 'gamma-Al2O3', 'SiO2', 'Silicalite-1', 'none'. |  |
| `synthesis` | str |  | no | Preparation method in a few words, e.g. 'incipient wetness, sequential'. |  |
| `pretreatment` | str |  | no | Reduction or activation before testing, e.g. 'H2, 600 C, 1 h'. |  |

## measurements.csv

| Column | Type | Unit | Required | Definition | Allowed |
|---|---|---|---|---|---|
| `measurement_id` | str |  | yes | Project ID, e.g. S0001-C03-M02. |  |
| `catalyst_id` | str |  | yes | Catalyst tested (links to catalysts.csv). |  |
| `location` | str |  | yes | Exactly where the value is in the paper, e.g. 'Table 2, row 3' or 'Fig. 4a, 2 h'. |  |
| `value_origin` | enum |  | yes | How the value was obtained. Digitized figure values carry extra uncertainty. | `table`, `text`, `figure_digitized`, `si_table`, `si_text`, `si_figure_digitized` |
| `heating_mode` | enum |  | yes | How the catalyst bed was heated. | `conventional`, `radio_frequency`, `induction`, `microwave`, `joule`, `plasma_assisted`, `other` |
| `temperature_C` | float | degC | yes | Reaction temperature as reported. | 200 to 1000 |
| `temperature_basis` | enum |  | yes | What the reported temperature measures. Critical for electrified heating, where the bed or particle surface can differ from the setpoint. | `setpoint`, `bed_thermocouple`, `wall_thermocouple`, `pyrometer`, `ir_camera`, `estimated`, `unreported` |
| `pressure_bar` | float | bar (absolute) | yes | Total absolute pressure. If the paper says 'atmospheric' and gives nothing else, enter 1.01325 and set pressure_assumed TRUE. | 0.01 to 50 |
| `pressure_assumed` | bool |  | yes | TRUE if pressure was not stated numerically and atmospheric was assumed. |  |
| `y_C3H8_in` | float | mole fraction | yes | Propane mole fraction in the reactor inlet (0-1). | 0.001 to 1 |
| `y_H2_in` | float | mole fraction | yes | Hydrogen co-feed mole fraction in the inlet (0 if none). | 0 to 0.99 |
| `y_C3H6_in` | float | mole fraction | no | Propylene co-feed mole fraction in the inlet (blank or 0 if none). | 0 to 0.99 |
| `diluent` | enum |  | yes | Inert diluent gas. | `none`, `N2`, `Ar`, `He`, `steam`, `mixed`, `unreported` |
| `whsv_h-1` | float | g C3H8 / (g cat h) | no | Weight hourly space velocity based on propane, as reported or computed. | 0.001 to 1000 |
| `whsv_source` | enum |  | no | Whether WHSV was stated in the paper or computed here from mass and flow. | `reported`, `computed` |
| `ghsv_h-1` | float | mL gas / (mL cat h) | no | Gas hourly space velocity, if reported instead of WHSV. | 1 to 10000000.0 |
| `catalyst_mass_mg` | float | mg | no | Catalyst mass loaded (excluding diluent such as quartz). | 0.1 to 1000000.0 |
| `total_flow_mL_min` | float | mL/min (STP as reported) | no | Total inlet gas flow. | 0.1 to 100000.0 |
| `time_on_stream_h` | float | h | yes | Time on stream at which the value was taken. Use 0 for 'initial' only if the paper gives no time, and say so in notes. | 0 to 10000 |
| `conversion_pct` | float | % | yes | Propane conversion reported at this point. | 0 to 100 |
| `conversion_basis` | enum |  | yes | How conversion was calculated, if the paper says. | `carbon_balance_products`, `propane_consumption`, `unreported` |
| `selectivity_C3H6_pct` | float | % | no | Propylene selectivity at this point. | 0 to 100 |
| `selectivity_basis` | enum |  | no | Carbon basis or molar basis. | `carbon_basis`, `molar_basis`, `unreported` |
| `yield_C3H6_pct` | float | % | no | Propylene yield if reported directly. | 0 to 100 |
| `carbon_balance_pct` | float | % | no | Carbon balance if reported. | 50 to 110 |
| `kd_reported_h-1` | float | 1/h | no | Deactivation constant exactly as reported by the authors. | -1 to 100 |
| `kd_definition` | str |  | no | The formula or wording the paper uses for its deactivation constant. |  |
| `test_duration_h` | float | h | no | Total length of the stability test this point belongs to. | 0 to 10000 |
| `run_label` | str |  | no | Points from the same continuous test share a label, e.g. 'Fig4a-stability'. Used to compute the common deactivation constant. Leave blank for single points. |  |
| `regeneration_cycle` | int |  | no | Cycle number if the paper reports regeneration cycles (1 = fresh). | 1 to 10000 |
| `extractor_flags` | str |  | no | Semicolon-separated issues noticed while extracting, e.g. 'temperature_ambiguous'. |  |
| `notes` | str |  | no | Free text. |  |

## quoted_equilibria.csv

| Column | Type | Unit | Required | Definition | Allowed |
|---|---|---|---|---|---|
| `quote_id` | str |  | yes | Project ID, e.g. S0004-Q01. |  |
| `source_id` | str |  | yes | Paper that quotes the value. |  |
| `location` | str |  | yes | Where the value is printed. |  |
| `temperature_C` | float | degC | yes | Temperature the quoted value refers to. | 200 to 1000 |
| `pressure_bar` | float | bar (absolute) | yes | Total absolute pressure. | 0.01 to 50 |
| `pressure_assumed` | bool |  | yes | TRUE if atmospheric was assumed. |  |
| `y_C3H8_in` | float | mole fraction | yes | Propane inlet mole fraction. | 0.001 to 1 |
| `y_H2_in` | float | mole fraction | yes | Hydrogen inlet mole fraction. | 0 to 0.99 |
| `X_eq_quoted_pct` | float | % | yes | Equilibrium conversion as printed. | 0 to 100 |
| `method_stated` | str |  | no | How the paper says it computed the value, if stated. |  |
| `notes` | str |  | no | Free text. |  |

## Computed columns (added by the pipeline, release table only)

| Column | Type | Unit | Definition |
|---|---|---|---|
| `X_eq_pct` | float | % | Equilibrium propane conversion at this row's temperature, pressure and inlet composition (code/pdh_equilibrium.py). |
| `approach_to_eq` | float | fraction | conversion_pct / X_eq_pct. 1.0 means the catalyst reached the ceiling. |
| `above_eq_flag` | bool |  | TRUE if reported conversion exceeds the ceiling by more than 2 percentage points. Usually means the reported temperature is not the true bed temperature, or a data-entry error. |
| `yield_C3H6_calc_pct` | float | % | conversion_pct x selectivity_C3H6_pct / 100. |
| `kd_std_h-1` | float | 1/h | Deactivation constant recomputed on one common definition, kd = [ln((1-Xf)/Xf) - ln((1-X0)/X0)] / t, from the first and last points of a run. Lets results from papers that define kd differently be compared. |
| `whsv_calc_h-1` | float | g C3H8 / (g cat h) | WHSV computed from flow, propane fraction and catalyst mass when the paper does not state it (ideal gas at 0 C, 1 atm). |

## Release table

`data/processed/openpdh_measurements.csv` contains every measurements column, the catalyst columns `family`, `label_in_paper`, `active_elements`, `support`, the source columns `source_id`, `doi`, `first_author`, `year`, and the computed columns above.
