# CausalAg-Net: Backend Implementation Guide

This document is a complete blueprint for the Backend Developer. It explains how the frontend expects the backend API to handle Authentication, Database storage, the Core Diagnostic Engine, and Explainable AI (Grad-CAM) integrations.

## 1. The Global Architecture
* **Frontend (Next.js)**: Handles the UI, routing, and stores Auth tokens.
* **Backend (FastAPI/Node.js)**: Strictly a JSON REST API. It handles user verification, database writes, and runs the AI models.
* **Database (PostgreSQL / MongoDB)**: Stores Users and their `DiagnosticHistory`.

> **CRITICAL RULE: NO SERVER-SIDE REDIRECTS!** Because the frontend is a React Single Page Application, your backend must never return a 302 Redirect (e.g., `return redirect("/dashboard")`). Your backend must return JSON tokens, and the frontend code will trigger the redirect in the user's browser.

---

## 2. Authentication Flow (JWT)

### A. The `/register` and `/login` Endpoints
The frontend sends a JSON POST request.

```json
POST /login
{
  "email": "farmer@kissan.ai",
  "password": "securepassword123"
}
```

Expected Response (Backend ➔ Frontend):
```json
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "Ramu"
  }
}
```

### B. Protecting the Backend Routes
Every subsequent request from the frontend to your backend will include this HTTP header: `Authorization: Bearer <access_token>`. Your backend must verify this JWT signature and return `401 Unauthorized` if invalid.

---

## 3. Database Integration Blueprint

**Table 1: Users**
* `id` (Primary Key)
* `email` (Unique)
* `password_hash` (Bcrypt encrypted)

**Table 2: DiagnosticHistory**
* `id` (Primary Key)
* `user_id` (Foreign Key)
* `image_url`
* `predicted_disease`
* `severity_score` (Float)
* `humidity_at_time` (Float)
* `ai_explanation` (Text)
* `gradcam_image_url` (String)

> **Workflow:** When a user hits `/diagnose`, after the AI runs, INSERT a row into `DiagnosticHistory` before returning the JSON.

---

## 4. PyTorch Model Integration (Deep Learning)

Because this project uses the custom CausalAg-Net (Neuro-Symbolic AI), your backend needs to load the PyTorch weights and execute inference on the uploaded image.

### A. Loading the Model on Startup
Do not load the 100MB+ `.pth` weights every time a user makes a request. Load the model once when the FastAPI server starts.

```python
import torch
from torchvision import transforms
from PIL import Image
import io
import base64

# Import the custom classes from your team's code
from backend.models.perception import VisualConceptExtractor
from backend.models.logic_engine import AgronomicLogicEngine

# Global variables for the model
perception_model = None
logic_engine = None
image_transforms = None

@app.on_event("startup")
async def load_ml_models():
    global perception_model, logic_engine, image_transforms
    
    print("Loading PyTorch Models into Memory...")
    
    # 1. Initialize the models
    perception_model = VisualConceptExtractor(num_concepts=5)
    
    # 2. Load the trained weights
    perception_model.load_state_dict(torch.load("weights/causal_ag_net_weights.pth", map_location="cpu"))
    perception_model.eval() # Set to evaluation mode!
    
    logic_engine = AgronomicLogicEngine()
    
    # 3. Define the image transformation pipeline
    image_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
```

---

## 5. Explainable AI (Grad-CAM) & Severity Estimation

In accordance with the NOVA framework for trustworthy AI, we need to return Explainable AI visual overlays (Grad-CAM) and severity scores to give farmers actionable and interpretable evidence.

### Executing Inference in the Endpoint

```python
import cv2
import numpy as np
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image

# Assume target_layers is defined for the perception_model
# e.g., target_layers = [perception_model.features[-1]]

@app.post("/diagnose")
async def run_diagnosis(
    image: UploadFile = File(...),
    manual_humidity: str = Form(...),
    manual_leaf_wetness: str = Form(...)
):
    # 1. Convert string form data to floats
    humidity_float = float(manual_humidity)
    wetness_float = float(manual_leaf_wetness)
    
    # 2. Read and convert image
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # We keep a numpy array version for Grad-CAM overlay later
    rgb_img = np.float32(pil_image.resize((224, 224))) / 255
    
    input_tensor = image_transforms(pil_image).unsqueeze(0)
    
    # 3. RUN NEURAL PERCEPTION & SEVERITY
    with torch.no_grad():
        concept_probs = perception_model(input_tensor)
        
        # Determine Severity based on lesion size/probability (NOVA logic)
        # Placeholder calculation based on concepts (e.g. necrotic lesion extent)
        severity_score = min((concept_probs[0][0].item() * 100) * 1.5, 100.0) 
        
    probs_list = concept_probs.squeeze().tolist()
    
    # 4. RUN SYMBOLIC LOGIC ENGINE
    env_tensor = torch.tensor([humidity_float, wetness_float])
    satisfaction_score = logic_engine.evaluate_rule(concept_probs, env_tensor)
    is_sound = satisfaction_score.item() > 0.8
    
    # 5. GENERATE GRAD-CAM OVERLAY (Explainable AI)
    # Enable gradients just for Grad-CAM
    cam = GradCAM(model=perception_model, target_layers=target_layers, use_cuda=False)
    grayscale_cam = cam(input_tensor=input_tensor, targets=None)[0, :]
    visualization = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)
    
    # Convert Grad-CAM image to base64 to send in JSON response
    _, buffer = cv2.imencode('.jpg', visualization)
    gradcam_base64 = base64.b64encode(buffer).decode('utf-8')
    
    # 6. Return the JSON structure
    return {
        "status": "success",
        "hypothesis": "Tomato_Late_Blight",
        "severity": f"{severity_score:.1f}%",
        "neural_perception": {
            "necrotic_lesions": probs_list[0],
            "water_soaked_spots": probs_list[1],
            "healthy_tissue": probs_list[2]
        },
        "environmental_state": {
            "high_humidity": humidity_float,
            "leaf_wetness_conducive": wetness_float
        },
        "logic_proof_trace": {
            "rule_evaluated": "If Late Blight THEN Water Soaked Spots AND High Humidity",
            "satisfaction_score": satisfaction_score.item(),
            "is_physically_sound": is_sound
        },
        "explainable_ai": {
            "gradcam_base64": f"data:image/jpeg;base64,{gradcam_base64}",
            "visual_focus": "Heatmap indicates regions of high probability for necrotic lesions."
        },
        "ai_explanation": "Based on the visual evidence of water-soaked spots (Grad-CAM heatmap) and high humidity inputs, the logic engine confirms the environmental factors align with Late Blight progression."
    }
```
