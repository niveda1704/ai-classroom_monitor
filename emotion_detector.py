"""
EmotionSense AI Classroom Monitor - Local Usage Script

This script loads the locally downloaded model and provides functions
for emotion detection in classroom settings.
"""

import os
import torch
from transformers import AutoModel, AutoTokenizer, AutoConfig, pipeline
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# Path to the locally downloaded model
MODEL_PATH = "./models/emotionsense-ai-classroom-monitor"

class EmotionSenseClassroom:
    """Class to handle emotion detection using the EmotionSense model."""
    
    def __init__(self, model_path=MODEL_PATH):
        """Initialize the emotion detection model."""
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
    def load_model(self):
        """Load the model from local directory."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. "
                "Please run download_model.py first."
            )
        
        print(f"Loading model from: {self.model_path}")
        
        try:
            # Try loading as a pipeline first (most common use case)
            self.pipeline = pipeline(
                task="image-classification",  # Adjust based on actual model type
                model=self.model_path,
                device=0 if self.device == "cuda" else -1
            )
            print("✅ Model loaded successfully as pipeline")
            
        except Exception as e:
            print(f"Pipeline loading failed: {e}")
            print("Trying alternative loading method...")
            
            try:
                # Try loading model and tokenizer separately
                self.config = AutoConfig.from_pretrained(self.model_path)
                self.model = AutoModel.from_pretrained(self.model_path)
                self.model.to(self.device)
                self.model.eval()
                
                # Try loading tokenizer if available
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                except:
                    print("No tokenizer found (might be an image model)")
                    
                print("✅ Model loaded successfully")
                
            except Exception as e2:
                print(f"❌ Error loading model: {e2}")
                raise
                
        return self
    
    def predict(self, input_data):
        """
        Make a prediction using the loaded model.
        
        Args:
            input_data: Image path, PIL Image, or text depending on model type
            
        Returns:
            Prediction results
        """
        if self.pipeline is not None:
            return self.pipeline(input_data)
        elif self.model is not None:
            # Handle direct model inference
            with torch.no_grad():
                # This needs to be customized based on the actual model type
                outputs = self.model(input_data)
                return outputs
        else:
            raise RuntimeError("Model not loaded. Call load_model() first.")
    
    def analyze_image(self, image_path):
        """
        Analyze an image for emotion detection.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with detected emotions and confidence scores
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
            
        results = self.predict(image_path)
        return results
    
    def analyze_classroom(self, image_paths):
        """
        Analyze multiple images from a classroom setting.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            List of results for each image
        """
        all_results = []
        for path in image_paths:
            try:
                result = self.analyze_image(path)
                all_results.append({
                    "image": path,
                    "emotions": result
                })
            except Exception as e:
                all_results.append({
                    "image": path,
                    "error": str(e)
                })
        return all_results


def main():
    """Main function to demonstrate model usage."""
    print("=" * 60)
    print("EmotionSense AI Classroom Monitor")
    print("=" * 60)
    
    # Initialize and load the model
    detector = EmotionSenseClassroom()
    
    try:
        detector.load_model()
        print("\n✅ Model is ready for use!")
        print("\nExample usage:")
        print("  detector.analyze_image('path/to/image.jpg')")
        print("  detector.analyze_classroom(['img1.jpg', 'img2.jpg'])")
        
        # Uncomment to test with an actual image:
        # result = detector.analyze_image("test_image.jpg")
        # print(f"Results: {result}")
        
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("Run 'python download_model.py' to download the model first.")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
