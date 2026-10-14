import io
from typing import Any, Dict, List, Tuple
import cv2
import numpy as np
from PIL import Image


class VisionEngine:
    """
    Local Computer Vision Engine using OpenCV and NumPy for deterministic visual signal extraction.
    No paid external API for color extraction or geometry analysis.
    """

    @staticmethod
    def extract_features_from_bytes(image_bytes: bytes, n_colors: int = 5) -> Dict[str, Any]:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            # Fallback using PIL if cv2 decode fails
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        height, width = img.shape[:2]

        # 1. Grayscale metrics
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))

        # 2. HSV metrics
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = float(np.mean(hsv[:, :, 1]))

        # 3. Edge density via Canny
        edges = cv2.Canny(gray, threshold1=100, threshold2=200)
        edge_pixels = np.count_nonzero(edges)
        edge_density = float(edge_pixels / (width * height))

        # 4. Color extraction with K-Means
        dominant_colors = VisionEngine._extract_kmeans_colors(img, n_clusters=n_colors)

        return {
            "width": width,
            "height": height,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "saturation": round(saturation, 2),
            "edge_density": round(edge_density, 4),
            "dominant_colors": dominant_colors,
        }

    @staticmethod
    def _extract_kmeans_colors(img_bgr: np.ndarray, n_clusters: int = 5) -> List[Dict[str, Any]]:
        # Downsample for computational speed
        max_dim = 200
        h, w = img_bgr.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        # Convert to RGB
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pixels = img_rgb.reshape(-1, 3).astype(np.float32)

        # Apply OpenCV K-Means
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        flags = cv2.KMEANS_PP_CENTERS
        compactness, labels, centers = cv2.kmeans(pixels, n_clusters, None, criteria, 10, flags)

        # Calculate cluster percentages
        labels = labels.flatten()
        counts = np.bincount(labels, minlength=n_clusters)
        total_pixels = len(labels)

        # Sort clusters by frequency descending
        sorted_indices = np.argsort(counts)[::-1]

        results = []
        for idx in sorted_indices:
            rgb = centers[idx].astype(int)
            r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
            pct = round(float(counts[idx] / total_pixels) * 100, 1)

            # Compute HEX
            hex_code = f"#{r:02X}{g:02X}{b:02X}"

            # Compute HSV using standard CV color conversion for single pixel
            pixel_rgb = np.uint8([[[r, g, b]]])
            pixel_hsv = cv2.cvtColor(pixel_rgb, cv2.COLOR_RGB2HSV)[0][0]
            hsv = [int(pixel_hsv[0]), int(pixel_hsv[1]), int(pixel_hsv[2])]

            results.append({
                "hex": hex_code,
                "rgb": [r, g, b],
                "hsv": hsv,
                "percentage": pct
            })

        return results


vision_engine = VisionEngine()
