import torch
import os
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from scipy.spatial.distance import cosine
from ...utils.spinner import Spinner

MODEL_CACHE = {}

def get_image_embedding(image_path: str, model_name: str = "facebook/dinov3-vitl16-pretrain-lvd1689m") -> list[float]:
    if model_name not in MODEL_CACHE:
        Spinner.set_message(self=Spinner, message=f"Loading model '{model_name}' into memory...")
        processor = AutoImageProcessor.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        MODEL_CACHE[model_name] = {"processor": processor, "model": model}

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


def find_similar_images(image_path: str = None, search_directory: str = None, top_k: int = 5, threshold: float = 0.5, **kwargs) -> list[dict]:
    """
    Finds the most visually similar images to a source image within a directory.
    This is a high-level tool that the LLM agent can call.

    CRITICAL: Use EXACT parameter names:
    - image_path (NOT reference_path, source_image, query_image, etc.)
    - search_directory (NOT search_folder, search_path, directory, etc.)
    - top_k (NOT max_results, limit, count, etc.)
    - threshold (NOT similarity_threshold, min_similarity, etc.)

    Args:
        image_path: The path to the source image file.
        search_directory: The directory to search for similar images.
        top_k: The number of top similar images to return.
        threshold: The similarity threshold for considering images as similar.
    """
    
    # Check for common wrong parameter names and provide helpful errors
    common_mistakes = {
        'query_image_path': 'image_path',
        'query': 'image_path', 
        'source_image': 'image_path',
        'reference_path': 'image_path',
        'query_image': 'image_path',
        'image': 'image_path',
        'source_path': 'image_path',
        'search_folder': 'search_directory',
        'search_path': 'search_directory', 
        'folder': 'search_directory',
        'directory': 'search_directory',
        'search_dir': 'search_directory',
        'max_results': 'top_k',
        'limit': 'top_k',
        'count': 'top_k',
        'num_results': 'top_k',
        'similarity_threshold': 'threshold',
        'min_similarity': 'threshold',
        'min_threshold': 'threshold'
    }
    
    if kwargs:
        wrong_params = []
        for wrong_name, correct_name in common_mistakes.items():
            if wrong_name in kwargs:
                wrong_params.append(f"'{wrong_name}' should be '{correct_name}'")
                # Auto-fix the parameter
                if correct_name == 'image_path' and image_path is None:
                    image_path = kwargs[wrong_name]
                elif correct_name == 'search_directory' and search_directory is None:
                    search_directory = kwargs[wrong_name]
                elif correct_name == 'top_k':
                    top_k = kwargs[wrong_name]
                elif correct_name == 'threshold':
                    threshold = kwargs[wrong_name]
        
        if wrong_params:
            error_msg = f"PARAMETER NAME ERROR: {', '.join(wrong_params)}. Use EXACT names: image_path, search_directory, top_k, threshold"
            return [{"error": error_msg, "corrected_call_example": {"image_path": "path/to/image.jpg", "search_directory": "folder/path", "top_k": 5, "threshold": 0.5}}]
    
    # Validate required parameters
    if image_path is None:
        return [{"error": "Missing required parameter 'image_path'. Must provide the path to the source image."}]
    if search_directory is None:
        return [{"error": "Missing required parameter 'search_directory'. Must provide the directory to search in."}]

    Spinner.set_message(self=Spinner, message=f"Finding images similar to '{image_path}' in '{search_directory}'...")

    source_embedding = get_image_embedding(image_path)
    if source_embedding is None:
        return {"error": "Failed to generate embedding for the source image."}
    
    similar_images = []

    for filename in os.listdir(search_directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.avif')):
            candidate_path = os.path.join(search_directory, filename)

            # Skip if it's the same file as the source
            try:
                if os.path.samefile(image_path, candidate_path):
                    continue
            except FileNotFoundError:
                # If files don't exist, compare paths as strings
                if os.path.abspath(image_path) == os.path.abspath(candidate_path):
                    continue

            Spinner.set_message(self=Spinner, message=f" - Analyzing {filename}...")
            comparison_embedding = get_image_embedding(candidate_path)

            if comparison_embedding:
                # Calculate similarity. Cosine distance is 1 - similarity.
                # So, similarity = 1 - distance
                similarity = 1 - cosine(source_embedding, comparison_embedding)
                similar_images.append({"file": filename, "similarity": similarity})

    # Sort the results by similarity score, highest first
    similar_images.sort(key=lambda x: x["similarity"], reverse=True)

    # Only return images above the threshold, up to top_k
    filtered = [img for img in similar_images if img["similarity"] >= threshold]
    return filtered[:top_k]