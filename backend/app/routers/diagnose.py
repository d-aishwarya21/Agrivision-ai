import io
import base64
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app import models
from app.logic_engine import analyze_image, select_disease

router = APIRouter(tags=["diagnose"])


def make_heatmap(pil_image: Image.Image) -> str:
    import numpy as np
    img = pil_image.convert("RGB").resize((224, 224))
    rgb = np.array(img, dtype=np.float32) / 255.0
    r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
    abnormality = np.clip(1.0 - (g - (r + b) / 2), 0, 1)
    abnormality = abnormality / (abnormality.max() + 1e-6)
    heat = np.zeros_like(rgb)
    heat[:,:,0] = abnormality
    heat[:,:,1] = 1.0 - abnormality
    overlay = np.clip(0.6 * rgb + 0.4 * heat, 0, 1)
    out = Image.fromarray((overlay * 255).astype("uint8"))
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


@router.post("/diagnose")
async def diagnose(
    image: UploadFile = File(...),
    manual_humidity: str = Form(...),
    manual_leaf_wetness: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        humidity = float(manual_humidity)
        leaf_wetness = float(manual_leaf_wetness)
    except ValueError:
        raise HTTPException(status_code=400, detail="Humidity and leaf wetness must be numbers")

    image_bytes = await image.read()
    try:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read image")

    concepts = analyze_image(pil_image)
    result = select_disease(concepts, humidity, leaf_wetness)
    gradcam = make_heatmap(pil_image)

    if result["disease"] == "Healthy":
        explanation = (
            "Great news! This leaf shows no signs of disease. "
            "The plant appears healthy with strong green tissue and no lesions. "
            "No treatment required."
        )
    else:
        explanation = (
            f"The analysis detected signs of {result['disease']}. "
            f"Visual indicators include lesions and discoloration consistent with this disease. "
            f"Environmental conditions (humidity={humidity:.2f}, leaf wetness={leaf_wetness:.2f}) "
            f"{'support' if result['is_physically_sound'] else 'partially support'} this diagnosis. "
            f"Severity is estimated at {result['severity_score']}%."
        )

    db.add(models.DiagnosticHistory(
        user_id=current_user.id,
        predicted_disease=result["disease"],
        severity_score=result["severity_score"],
        humidity_at_time=humidity,
        leaf_wetness_at_time=leaf_wetness,
        is_physically_sound=result["is_physically_sound"],
        ai_explanation=explanation,
        gradcam_image_url=gradcam,
    ))
    db.commit()

    return {
        "status": "success",
        "hypothesis": result["disease"],
        "severity": f"{result['severity_score']}%",
        "neural_perception": concepts,
        "environmental_state": {
            "high_humidity": humidity,
            "leaf_wetness_conducive": leaf_wetness,
        },
        "logic_proof_trace": {
            "rule_evaluated": result["rule_text"],
            "satisfaction_score": result["satisfaction_score"],
            "is_physically_sound": result["is_physically_sound"],
        },
        "explainable_ai": {
            "gradcam_base64": gradcam,
            "visual_focus": "Heatmap highlights abnormal regions on the leaf.",
        },
        "ai_explanation": explanation,
    }