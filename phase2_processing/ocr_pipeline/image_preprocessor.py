"""
Image preprocessing pipeline using OpenCV.
Prepares scanned images for optimal OCR accuracy.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Preprocesses scanned images to improve OCR accuracy.
    Applies deskewing, binarization, and noise removal.
    """

    def __init__(self):
        self.stats = {
            'processed': 0,
            'deskewed': 0,
            'failed': 0
        }

    def preprocess_image(self, image_path: str, save_intermediate: bool = False) -> np.ndarray:
        """
        Complete preprocessing pipeline for a scanned image.

        Args:
            image_path: Path to image file
            save_intermediate: If True, save intermediate processing steps

        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            if save_intermediate:
                self._save_step(image, image_path, "01_original")

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if save_intermediate:
                self._save_step(gray, image_path, "02_grayscale")

            # Deskew (correct rotation)
            deskewed, angle = self.deskew_image(gray)
            if abs(angle) > 0.5:
                self.stats['deskewed'] += 1
            if save_intermediate:
                self._save_step(deskewed, image_path, f"03_deskewed_{angle:.2f}deg")

            # Binarization (adaptive thresholding)
            binary = self.binarize_image(deskewed)
            if save_intermediate:
                self._save_step(binary, image_path, "04_binary")

            # Noise removal
            denoised = self.remove_noise(binary)
            if save_intermediate:
                self._save_step(denoised, image_path, "05_denoised")

            self.stats['processed'] += 1
            logger.info(f"Preprocessed {image_path} (rotated {angle:.2f}°)")

            return denoised

        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Preprocessing failed for {image_path}: {e}")
            # Return original grayscale as fallback
            try:
                return cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2GRAY)
            except:
                return None

    def deskew_image(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detect and correct skew/rotation in scanned images.

        Args:
            image: Grayscale image as numpy array

        Returns:
            Tuple of (deskewed image, rotation angle in degrees)
        """
        # Use Hough transform to detect lines and determine skew
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

        if lines is None:
            return image, 0.0

        # Calculate angles of detected lines
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            angles.append(angle)

        if not angles:
            return image, 0.0

        # Use median angle to determine skew
        median_angle = np.median(angles)

        # Only correct if skew is significant (> 0.5 degrees)
        if abs(median_angle) < 0.5:
            return image, 0.0

        # Rotate image to correct skew
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated, median_angle

    def binarize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Convert grayscale image to pure black and white using adaptive thresholding.
        This removes shadows, gradients, and background noise.

        Args:
            image: Grayscale image

        Returns:
            Binarized image
        """
        # Adaptive thresholding works better than global thresholding for scanned docs
        binary = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,  # Size of neighborhood
            C=2  # Constant subtracted from mean
        )

        return binary

    def remove_noise(self, image: np.ndarray) -> np.ndarray:
        """
        Remove salt-and-pepper noise using morphological operations.

        Args:
            image: Binary image

        Returns:
            Denoised image
        """
        # Morphological opening (erosion followed by dilation)
        # Removes small white noise on black background
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=1)

        # Morphological closing (dilation followed by erosion)
        # Removes small black noise on white background
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Median blur to remove remaining noise
        denoised = cv2.medianBlur(closing, 3)

        return denoised

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Args:
            image: Grayscale image

        Returns:
            Contrast-enhanced image
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced

    def _save_step(self, image: np.ndarray, original_path: str, step_name: str):
        """Save intermediate processing step for debugging."""
        output_dir = Path(original_path).parent / "preprocessing_steps"
        output_dir.mkdir(exist_ok=True)

        filename = Path(original_path).stem
        output_path = output_dir / f"{filename}_{step_name}.png"

        cv2.imwrite(str(output_path), image)


if __name__ == "__main__":
    # Test the preprocessor
    logging.basicConfig(level=logging.INFO)
    preprocessor = ImagePreprocessor()

    # Example usage
    # preprocessed = preprocessor.preprocess_image('scanned_page.png', save_intermediate=True)
    # cv2.imwrite('preprocessed_output.png', preprocessed)
