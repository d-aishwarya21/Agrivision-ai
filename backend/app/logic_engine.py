import json
import os

RULES_PATH = os.path.join(os.path.dirname(__file__), "agronomic_rules.json")

with open(RULES_PATH, "r") as f:
    RULES = json.load(f)


def analyze_image(pil_image):
    import numpy as np
    img = pil_image.convert("RGB").resize((224, 224))
    rgb = np.array(img, dtype=np.float32) / 255.0
    r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
    total = r.size

    green = ((g > 0.25) & (g > r) & (g > b)).sum() / total
    brown = ((r > 0.35) & (g < 0.3) & (b < 0.25)).sum() / total
    dark  = ((r < 0.3) & (g < 0.3) & (b < 0.3)).sum() / total
    yellow = ((r > 0.5) & (g > 0.4) & (b < 0.3)).sum() / total

    return {
        "healthy_tissue": float(min(green * 1.5, 1.0)),
        "necrotic_lesions": float(min(brown * 2.5, 1.0)),
        "water_soaked_spots": float(min(dark * 2.0, 1.0)),
        "chlorotic_halos": float(min(yellow * 2.0, 1.0)),
        "concentric_rings": float(min(brown * 1.5, 1.0)),
        "velvety_spots": float(min(dark * 1.5, 1.0)),
        "leaf_curling": float(min((1 - green) * 0.5, 1.0)),
    }


def select_disease(concepts, humidity, leaf_wetness):
    best = None
    best_score = -1.0

    for disease, rule in RULES.items():
        required = rule.get("visual_concepts_required", [])
        if required:
            concept_score = sum(concepts.get(c, 0.0) for c in required) / len(required)
        else:
            concept_score = 0.0

        env = rule.get("environmental_conditions", {})
        min_hum = env.get("min_humidity", 0.0)
        needs_wet = env.get("leaf_wetness_required", False)

        env_score = 0.5 if humidity >= min_hum else 0.2
        env_score += 0.5 if (not needs_wet or leaf_wetness >= 0.5) else 0.0

        score = 0.7 * concept_score + 0.3 * env_score

        if score > best_score:
            best_score = score
            best = disease

    rule = RULES.get(best, {})
    multiplier = rule.get("severity_multiplier", 1.0)
    severity = round(min(best_score * 100 * multiplier, 100.0), 1)
    is_sound = best_score > 0.8
    rule_text = rule.get("logic_rule_text", "")

    return {
        "disease": best,
        "severity_score": severity,
        "satisfaction_score": round(best_score, 4),
        "is_physically_sound": is_sound,
        "rule_text": rule_text,
    }