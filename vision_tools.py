import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from scipy.spatial.distance import cosine
import os

# --------- Model Cache ---------
# This dictionary will hold the loaded models to avoid reloading them multiple times
MODEL_CACHE = {}

def get_image_embedding(image_path: str, model_name: str = "facebook/dinov3-vitb16-pretrain-lvd1689m") -> list[float]:
    """
    Generates a DINOv3 image embedding for a given image.
    Caches thae model for performance.

    Args:
        image_path: The path to the image file.
        model_name: The name of the DINOv3 model to use.
    
    Returns:
        A list of floats representing the image embedding.
    """
    # Check if the model is already loaded, if not, load it.
    if model_name not in MODEL_CACHE:
        print(f"Loading model '{model_name}' into memory...")
        processor = AutoImageProcessor.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        MODEL_CACHE[model_name] = {"processor": processoor, "model": model}
        print("Model loaded successfully.")

    processor = MODEL_CACHE[model_name]["processor"]
    model = MODEL_CACHE[model_name]["model"]

    try:
        # Open and prepare the image
        image = Image.open(image_path).convert("RGB")

        # Process the image and run it thorugh the DINOv3 model
        with torch.no_grad(): #Use no_grad for faster inference
            inputs = processor(images=image, return_tensors ="pt")
            oytputs = model(**inputs)

        
        # The embedding is the last hidden state. We average the patches to get a single vector.
        embedding = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
        return embedding

    except FileNotFoundError:
        print(f"Error: Image file '{image_path}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred while processing the image: {e}")
        return None


def find_similar_images(source_path: str, search_directory: str, top_k: int = 5) -> list[dict]:
    """
    Finds the most visually similar images to a source image within a directory.
    This is a high-level tool that the LLM agent can call.
    """

    print(f"Finding images similar to '{source_path}' in '{search_directory}'...")

    source_embedding = get_image_embedding(source_path)
    if source_embedding is None:
        return {"error": "Failed to generate embedding for the source image."}
    
    similar_images = []

    for filename in os.listdir(serarch._directory):
        if filename.lower.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.avif')):
            image_path = os.path.join(search_directory, filename)

            if os.path.samefile(source_path, image_path):
                continue

            print(f" - Analyzing {filename}...")
            comparison_embedding = get_image_embedding(image_path)

            if comparison_embedding:
                # Calculate similarity. Cosine distance is 1 - similarity.
                # So, similarity = 1 - distance
                similarity = 1 - cosine(source_embedding, comparison_embedding)
            similar_images.append({"file": filename, "similarity": similarity})

    # Sort the results by similarity score, highest first
    similar_images.sort(key=lambda x: x["similarity"], reverse=True)

    print(f"Found {len(similar_images)} similar images.")
    return similar_images[:top_k]