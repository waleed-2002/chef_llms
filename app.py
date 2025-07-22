from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import requests
import gradio as gr
import uvicorn
from PIL import Image, ImageDraw
import io

# === FastAPI app ===
app = FastAPI(title="Chef AI Recipe & Image Generator")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === External API endpoints ===
RECIPE_API_URL = "https://pys7h0wkhesomy-8888.proxy.runpod.net/generate-recipe"
IMAGE_API_URL = "https://pys7h0wkhesomy-8888.proxy.runpod.net/generate-image"

# === Pydantic model ===
class RecipeRequest(BaseModel):
    user_input: str

# === Health check ===
@app.get("/health")
def health_check():
    return {"status": "ok"}

# === Redirect root to docs ===
@app.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse(url="/docs")

# === Recipe generator endpoint ===
@app.post("/generate-recipe")
def generate_recipe(request: RecipeRequest):
    response = requests.post(
        RECIPE_API_URL,
        headers={"Content-Type": "application/json"},
        json={"user_input": request.user_input}
    )
    if response.status_code == 200:
        return response.json()
    return {"error": "Failed to generate recipe", "details": response.text}

# === Placeholder Image (used on image generation error) ===
def create_placeholder_image(text="No Image"):
    img = Image.new("RGB", (512, 512), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.text((10, 250), text, fill=(0, 0, 0))
    return img

# === Gradio function ===
def gradio_generate_all(user_input):
    # === Recipe ===
    try:
        recipe_response = requests.post(
            RECIPE_API_URL,
            headers={"Content-Type": "application/json"},
            json={"user_input": user_input}
        )
        recipe = recipe_response.json().get("recipe", "No recipe returned.")
    except Exception as e:
        recipe = f"Recipe generation failed: {e}"

    # === Image ===
    try:
        image_response = requests.post(
            IMAGE_API_URL,
            headers={"Content-Type": "application/json"},
            json={"prompt": user_input}
        )
        image = Image.open(io.BytesIO(image_response.content))
    except Exception as e:
        print(f"Image generation failed: {e}")
        image = create_placeholder_image("Image generation failed")

    return recipe, image

# === Gradio UI ===
gradio_interface = gr.Interface(
    fn=gradio_generate_all,
    inputs=gr.Textbox(lines=3, placeholder="Enter ingredients or a recipe idea...", label="Your Request"),
    outputs=[
        gr.Textbox(label="Generated Recipe", lines=20, interactive=False),
        gr.Image(type="pil", label="Generated Food Image")
    ],
    title="Chef AI - Recipe & Image Generator",
    description="Enter ingredients or a cooking idea. Chef AI will generate a recipe and a matching image!"
)

# === Run Gradio at startup in thread ===
@app.on_event("startup")
def launch_gradio():
    import threading
    threading.Thread(target=lambda: gradio_interface.launch(share=True, server_port=8080, server_name="0.0.0.0")).start()

# === Run FastAPI server ===
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
