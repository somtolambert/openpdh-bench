"""schema.py: the single definition of every column in the benchmark.

Plain-language note: this file is the master list of columns. The codebook
(docs/CODEBOOK.md) and the quality checks are both generated from it, so they
can never disagree. To add or change a column, change it here only.

Three tables, linked by IDs:
  sources.csv       one row per paper
  catalysts.csv     one row per catalyst as named in a paper
  measurements.csv  one row per reported test point (catalyst x condition x time on stream)
"""

HEATING_MODES = ["conventional", "radio_frequency", "induction", "microwave", "joule", "plasma_assisted", "other"]
TEMP_BASIS = ["setpoint", "bed_thermocouple", "wall_thermocouple", "pyrometer", "ir_camera", "estimated", "unreported"]
VALUE_ORIGIN = ["table", "text", "figure_digitized", "si_table", "si_text", "si_figure_digitized"]
CONV_BASIS = ["carbon_balance_products", "propane_consumption", "unreported"]
SEL_BASIS = ["carbon_basis", "molar_basis", "unreported"]
FAMILIES = ["Pt", "Pt-Sn", "Pt-Ga", "Pt-Zn", "Pt-In", "Pt-other", "CrOx", "GaOx", "ZnOx", "VOx", "Co", "Fe",
            "Ni", "In", "Sn", "Zr", "Pt-Ge", "carbon", "zeolite_metal_free", "other"]
DILUENTS = ["none", "N2", "Ar", "He", "steam", "mixed", "unreported"]

# Each column: (name, type, unit, required, definition, allowed values or (min, max))
SOURCES = [
    ("source_id", "str", "", True, "Project ID for the paper, e.g. S0001. Never reused.", None),
    ("doi", "str", "", True, "DOI of the paper, lower case, without https://doi.org/.", None),
    ("first_author", "str", "", True, "Family name of the first author.", None),
    ("year", "int", "", True, "Year of the version of record.", (1950, 2030)),
    ("journal", "str", "", True, "Journal or venue name as printed.", None),
    ("open_access", "bool", "", True, "TRUE if the full text is free to read at the DOI.", None),
    ("curated_by", "str", "", True, "Initials of the person responsible for the entry.", None),
    ("extraction_date", "date", "", True, "ISO date the values were entered.", None),
    ("verified_by", "str", "", False, "Initials of the person who checked the values against the paper. Blank until checked.", None),
    ("verified_date", "date", "", False, "ISO date of the second check.", None),
    ("notes", "str", "", False, "Anything a reader needs about this paper as a whole.", None),
]

CATALYSTS = [
    ("catalyst_id", "str", "", True, "Project ID, e.g. S0001-C03 (source ID + catalyst number).", None),
    ("source_id", "str", "", True, "Paper this catalyst comes from (links to sources.csv).", None),
    ("label_in_paper", "str", "", True, "The catalyst's name exactly as the paper writes it, e.g. 'PtSn/Al2O3-0.5'.", None),
    ("family", "enum", "", True, "Active-phase family, used for grouping.", FAMILIES),
    ("active_elements", "str", "", True, "Active and promoter elements with nominal loading, "
     "semicolon-separated 'Element:wt%' pairs, e.g. 'Pt:0.5;Sn:1.0'. Use 'na' for loading not reported.", None),
    ("loading_basis", "enum", "", True, "Whether loadings are nominal (as prepared) or measured (ICP, XRF, etc.).",
     ["nominal", "measured", "unreported"]),
    ("support", "str", "", True, "Support material as written, e.g. 'gamma-Al2O3', 'SiO2', 'Silicalite-1', 'none'.", None),
    ("synthesis", "str", "", False, "Preparation method in a few words, e.g. 'incipient wetness, sequential'.", None),
    ("pretreatment", "str", "", False, "Reduction or activation before testing, e.g. 'H2, 600 C, 1 h'.", None),
]

MEASUREMENTS = [
    ("measurement_id", "str", "", True, "Project ID, e.g. S0001-C03-M02.", None),
    ("catalyst_id", "str", "", True, "Catalyst tested (links to catalysts.csv).", None),
    ("location", "str", "", True, "Exactly where the value is in the paper, e.g. 'Table 2, row 3' or 'Fig. 4a, 2 h'.", None),
    ("value_origin", "enum", "", True, "How the value was obtained. Digitized figure values carry extra uncertainty.", VALUE_ORIGIN),
    ("heating_mode", "enum", "", True, "How the catalyst bed was heated.", HEATING_MODES),
    ("temperature_C", "float", "degC", True, "Reaction temperature as reported.", (200, 1000)),
    ("temperature_basis", "enum", "", True, "What the reported temperature measures. Critical for electrified heating, "
     "where the bed or particle surface can differ from the setpoint.", TEMP_BASIS),
    ("pressure_bar", "float", "bar (absolute)", True, "Total absolute pressure. If the paper says 'atmospheric' "
     "and gives nothing else, enter 1.01325 and set pressure_assumed TRUE.", (0.01, 50)),
    ("pressure_assumed", "bool", "", True, "TRUE if pressure was not stated numerically and atmospheric was assumed.", None),
    ("y_C3H8_in", "float", "mole fraction", True, "Propane mole fraction in the reactor inlet (0-1).", (0.001, 1)),
    ("y_H2_in", "float", "mole fraction", True, "Hydrogen co-feed mole fraction in the inlet (0 if none).", (0, 0.99)),
    ("y_C3H6_in", "float", "mole fraction", False, "Propylene co-feed mole fraction in the inlet (blank or 0 if none).", (0, 0.99)),
    ("diluent", "enum", "", True, "Inert diluent gas.", DILUENTS),
    ("whsv_h-1", "float", "g C3H8 / (g cat h)", False, "Weight hourly space velocity based on propane, as reported or computed.", (0.001, 1000)),
    ("whsv_source", "enum", "", False, "Whether WHSV was stated in the paper or computed here from mass and flow.",
     ["reported", "computed", ""]),
    ("ghsv_h-1", "float", "mL gas / (mL cat h)", False, "Gas hourly space velocity, if reported instead of WHSV.", (1, 1e7)),
    ("catalyst_mass_mg", "float", "mg", False, "Catalyst mass loaded (excluding diluent such as quartz).", (0.1, 1e6)),
    ("total_flow_mL_min", "float", "mL/min (STP as reported)", False, "Total inlet gas flow.", (0.1, 1e5)),
    ("time_on_stream_h", "float", "h", True, "Time on stream at which the value was taken. Use 0 for 'initial' "
     "only if the paper gives no time, and say so in notes.", (0, 10000)),
    ("conversion_pct", "float", "%", True, "Propane conversion reported at this point.", (0, 100)),
    ("conversion_basis", "enum", "", True, "How conversion was calculated, if the paper says.", CONV_BASIS),
    ("selectivity_C3H6_pct", "float", "%", False, "Propylene selectivity at this point.", (0, 100)),
    ("selectivity_basis", "enum", "", False, "Carbon basis or molar basis.", SEL_BASIS + [""]),
    ("yield_C3H6_pct", "float", "%", False, "Propylene yield if reported directly.", (0, 100)),
    ("carbon_balance_pct", "float", "%", False, "Carbon balance if reported.", (50, 110)),
    ("kd_reported_h-1", "float", "1/h", False, "Deactivation constant exactly as reported by the authors.", (-1, 100)),
    ("kd_definition", "str", "", False, "The formula or wording the paper uses for its deactivation constant.", None),
    ("test_duration_h", "float", "h", False, "Total length of the stability test this point belongs to.", (0, 10000)),
    ("run_label", "str", "", False, "Points from the same continuous test share a label, e.g. 'Fig4a-stability'. "
     "Used to compute the common deactivation constant. Leave blank for single points.", None),
    ("regeneration_cycle", "int", "", False, "Cycle number if the paper reports regeneration cycles (1 = fresh).", (1, 10000)),
    ("extractor_flags", "str", "", False, "Semicolon-separated issues noticed while extracting, e.g. 'temperature_ambiguous'.", None),
    ("notes", "str", "", False, "Free text.", None),
]

# Equilibrium conversions that papers themselves quote. Used to test both the
# calculator and the papers: large disagreements are reported in the QA report.
QUOTED_EQ = [
    ("quote_id", "str", "", True, "Project ID, e.g. S0004-Q01.", None),
    ("source_id", "str", "", True, "Paper that quotes the value.", None),
    ("location", "str", "", True, "Where the value is printed.", None),
    ("temperature_C", "float", "degC", True, "Temperature the quoted value refers to.", (200, 1000)),
    ("pressure_bar", "float", "bar (absolute)", True, "Total absolute pressure.", (0.01, 50)),
    ("pressure_assumed", "bool", "", True, "TRUE if atmospheric was assumed.", None),
    ("y_C3H8_in", "float", "mole fraction", True, "Propane inlet mole fraction.", (0.001, 1)),
    ("y_H2_in", "float", "mole fraction", True, "Hydrogen inlet mole fraction.", (0, 0.99)),
    ("X_eq_quoted_pct", "float", "%", True, "Equilibrium conversion as printed.", (0, 100)),
    ("method_stated", "str", "", False, "How the paper says it computed the value, if stated.", None),
    ("notes", "str", "", False, "Free text.", None),
]

TABLES = {"sources": SOURCES, "catalysts": CATALYSTS, "measurements": MEASUREMENTS, "quoted_equilibria": QUOTED_EQ}

# Columns added by the pipeline (not entered by hand). v1.1 comparison layer.
DERIVED = [
    ("X_eq_pct", "float", "%", "Equilibrium propane conversion at this row's temperature, pressure and inlet "
     "composition (code/pdh_equilibrium.py)."),
    ("approach_to_eq", "float", "fraction", "conversion_pct / X_eq_pct. 1.0 means the catalyst reached the ceiling."),
    ("above_eq_flag", "bool", "", "TRUE if reported conversion exceeds the ceiling by more than 2 percentage points. "
     "Usually means the reported temperature is not the true bed temperature, or a data-entry error."),
    ("yield_C3H6_calc_pct", "float", "%", "conversion_pct x selectivity_C3H6_pct / 100."),
    ("kd_std_h-1", "float", "1/h", "Deactivation constant recomputed on one common definition, "
     "kd = [ln((1-Xf)/Xf) - ln((1-X0)/X0)] / t, from the first and last points of a run. "
     "Lets results from papers that define kd differently be compared."),
    ("whsv_calc_h-1", "float", "g C3H8 / (g cat h)", "WHSV computed from flow, propane fraction and catalyst mass "
     "when the paper does not state it (ideal gas at 0 C, 1 atm)."),
]
