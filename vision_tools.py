import torch
import os
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from scipy.spatial.distance import cosine
from utils import Spinner

# --------- Model Cache ---------
# This dictionary will hold the loaded models to avoid reloading them multiple times
MODEL_CACHE = {}

def get_image_embedding(image_path: str, model_name: str = "facebook/dinov3-vitl16-pretrain-lvd1689m") -> list[float]:
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
        Spinner.set_message(self=Spinner, message=f"Loading model '{model_name}' into memory...")
        processor = AutoImageProcessor.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        MODEL_CACHE[model_name] = {"processor": processor, "model": model}
        # print("Model loaded successfully.")

    processor = MODEL_CACHE[model_name]["processor"]
    model = MODEL_CACHE[model_name]["model"]

    try:
        # Open and prepare the image
        image = Image.open(image_path).convert("RGB")

        # Process the image and run it thorugh the DINOv3 model
        with torch.no_grad(): #Use no_grad for faster inference
            inputs = processor(images=image, return_tensors ="pt")
            outputs = model(**inputs)

        
        # The embedding is the last hidden state. We average the patches to get a single vector.
        embedding = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
        return embedding

    except FileNotFoundError:
        print(f"Error: Image file '{image_path}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred while processing the image: {e}")
        return None


def find_similar_images(image_path: str, search_directory: str, top_k: int = 5, threshold: float = 0.5) -> list[dict]:
    """
    Finds the most visually similar images to a image image within a directory.
    This is a high-level tool that the LLM agent can call.

    Args:
        image_path: The path to the source image file.
        search_directory: The directory to search for similar images.
        top_k: The number of top similar images to return.
        threshold: The similarity threshold for considering images as similar.
    """

    Spinner.set_message(self=Spinner, message=f"Finding images similar to '{image_path}' in '{search_directory}'...")

    image_embedding = get_image_embedding(image_path)
    if image_embedding is None:
        return {"error": "Failed to generate embedding for the source image."}
    
    similar_images = []

    for filename in os.listdir(search_directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.avif')):
            image_path = os.path.join(search_directory, filename)

            if os.path.samefile(image_path, image_path):
                continue

            Spinner.set_message(self=Spinner, message=f" - Analyzing {filename}...")
            comparison_embedding = get_image_embedding(image_path)

            if comparison_embedding:
                # Calculate similarity. Cosine distance is 1 - similarity.
                # So, similarity = 1 - distance
                similarity = 1 - cosine(image_embedding, comparison_embedding)
            similar_images.append({"file": filename, "similarity": similarity})

    # Sort the results by similarity score, highest first
    similar_images.sort(key=lambda x: x["similarity"], reverse=True)

    # print(f"Found {len(similar_images)} images.")
    # Only return images above the threshold, up to top_k
    filtered = [img for img in similar_images if img["similarity"] >= threshold]
    return filtered[:top_k]