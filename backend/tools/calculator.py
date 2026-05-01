import re
from typing import Optional


# ── Formula Registry ──────────────────────────────────────────────────────────
FORMULAS: dict[str, dict] = {
    "max_building_height": {
        "formula": "max_height = street_width × 1.5",
        "fn": lambda p: p["street_width"] * 1.5,
        "inputs": ["street_width"],
        "unit": "meters",
        "law_ref": "Unified Building Law 119/2008 & Decree 943/2024",
        "description_ar": "الحد الأقصى لارتفاع المبنى = عرض الشارع × 1.5",
        "description_en": "Maximum building height = street width × 1.5",
    },
    "required_parking_spots": {
        "formula": "spots = ⌈GFA / parking_ratio⌉",
        "fn": lambda p: -(-int(p["gfa"]) // int(p["parking_ratio"])),
        "inputs": ["gfa", "parking_ratio"],
        "unit": "spots",
        "law_ref": "Parking/Garage Code",
        "description_ar": "عدد المواقف المطلوبة = إجمالي المساحة المبنية ÷ نسبة الموقف",
        "description_en": "Required parking spots = ⌈GFA / parking ratio⌉",
    },
    "building_coverage_ratio": {
        "formula": "coverage = (built_area / lot_area) × 100",
        "fn": lambda p: (p["built_area"] / p["lot_area"]) * 100,
        "inputs": ["built_area", "lot_area"],
        "unit": "%",
        "law_ref": "Unified Building Law 119/2008",
        "description_ar": "نسبة البناء = المساحة المبنية ÷ مساحة الأرض × 100",
        "description_en": "Building coverage ratio = built area / lot area × 100",
    },
    "setback_distance": {
        "formula": "setback = lot_width × setback_factor",
        "fn": lambda p: p["lot_width"] * p["setback_factor"],
        "inputs": ["lot_width", "setback_factor"],
        "unit": "meters",
        "law_ref": "Unified Building Law 119/2008",
        "description_ar": "مسافة الارتداد = عرض القطعة × معامل الارتداد",
        "description_en": "Setback distance = lot width × setback factor",
    },
}

# ── Detection ─────────────────────────────────────────────────────────────────

def detect_calculation_type(query: str) -> Optional[str]:
    q = query.lower()
    if any(k in q for k in ["ارتفاع", "height", "طابق", "floor", "storey"]):
        return "max_building_height"
    if any(k in q for k in ["موقف", "parking", "جراج", "garage"]):
        return "required_parking_spots"
    if any(k in q for k in ["نسبة البناء", "coverage", "built area", "مساحة مبنية"]):
        return "building_coverage_ratio"
    if any(k in q for k in ["تراجع", "setback", "ارتداد", "إرتداد"]):
        return "setback_distance"
    return None


def extract_numbers(text: str) -> list[float]:
    """Extract numeric values from text including Arabic-Indic numerals."""
    arabic_to_latin = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    converted = text.translate(arabic_to_latin)
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", converted)]


# ── Execution ─────────────────────────────────────────────────────────────────

def run_calculation(calc_type: str, params: dict) -> dict:
    """Execute a registered formula with validated parameters."""
    formula_def = FORMULAS.get(calc_type)
    if not formula_def:
        return {"error": f"Unknown calculation type: '{calc_type}'"}

    missing = [k for k in formula_def["inputs"] if k not in params or params[k] is None]
    if missing:
        return {
            "error": f"Missing required parameters: {missing}",
            "required_inputs": formula_def["inputs"],
        }

    try:
        result = formula_def["fn"](params)
        return {
            "calculation_type": calc_type,
            "formula": formula_def["formula"],
            "inputs": params,
            "result": round(float(result), 2),
            "unit": formula_def["unit"],
            "law_reference": formula_def["law_ref"],
            "description_ar": formula_def["description_ar"],
            "description_en": formula_def["description_en"],
        }
    except Exception as exc:
        return {"error": str(exc)}
