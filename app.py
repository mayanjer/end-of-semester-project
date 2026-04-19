import streamlit as st
import cv2
import numpy as np
from skimage.filters import threshold_local
from skimage import measure
import pytesseract
import imutils
import os
import re
import requests
from pathlib import Path

import cv2
import numpy as np
from skimage.filters import threshold_local
from skimage import measure
import pytesseract
import imutils
import os
import re
import requests
from pathlib import Path

print("✓ All imports successful")

def sort_cont(character_contours):
    """
    Sort contours from left to right
    """
    i = 0
    boundingBoxes = [cv2.boundingRect(c) for c in character_contours]
     
    (character_contours, boundingBoxes) = zip(*sorted(zip(character_contours,
                                                          boundingBoxes),
                                                      key = lambda b: b[1][i],
                                                      reverse = False))
     
    return character_contours


def segment_chars(plate_img, fixed_width):
    """
    Extract Value channel from the HSV format of image
    and apply adaptive thresholding to reveal characters
    on the license plate
    """
    V = cv2.split(cv2.cvtColor(plate_img, cv2.COLOR_BGR2HSV))[2]

    thresh = cv2.adaptiveThreshold(V, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY,
                                   11, 2)
  
    thresh = cv2.bitwise_not(thresh)
 
    # resize the license plate region to a canonical size
    plate_img = imutils.resize(plate_img, width = fixed_width)
    thresh = imutils.resize(thresh, width = fixed_width)
    bgr_thresh = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
 
    # perform a connected components analysis
    labels = measure.label(thresh, background = 0)
    charCandidates = np.zeros(thresh.shape, dtype ='uint8')
 
    # loop over the unique components
    characters = []
    for label in np.unique(labels):
         
        # if this is the background label, ignore it
        if label == 0:
            continue
        
        # construct the label mask
        labelMask = np.zeros(thresh.shape, dtype ='uint8')
        labelMask[labels == label] = 255
 
        cnts = cv2.findContours(labelMask,
                     cv2.RETR_EXTERNAL,
                     cv2.CHAIN_APPROX_SIMPLE)

        cnts = cnts[1] if imutils.is_cv3() else cnts[0]
 
        # ensure at least one contour was found
        if len(cnts) > 0:
 
            # grab the largest contour
            c = max(cnts, key = cv2.contourArea)
            (boxX, boxY, boxW, boxH) = cv2.boundingRect(c)
 
            # compute the aspect ratio, solidity, and height ratio
            aspectRatio = boxW / float(boxH) if boxH != 0 else 0
            solidity = cv2.contourArea(c) / float(boxW * boxH) if (boxW * boxH) != 0 else 0
            heightRatio = boxH / float(plate_img.shape[0]) if plate_img.shape[0] != 0 else 0
 
            # determine if the aspect ratio, solidity, and height pass tests
            keepAspectRatio = aspectRatio < 1.0
            keepSolidity = solidity > 0.15
            keepHeight = heightRatio > 0.5 and heightRatio < 0.95
 
            # check if the component passes all tests
            if keepAspectRatio and keepSolidity and keepHeight and boxW > 14:
                 
                # compute the convex hull
                hull = cv2.convexHull(c)
                cv2.drawContours(charCandidates, [hull], -1, 255, -1)
 
    contours, hier = cv2.findContours(charCandidates,
                                         cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_SIMPLE)
     
    if contours:
        contours = sort_cont(contours)
         
        # value to be added to each dimension of the character
        addPixel = 4 
        for c in contours:
            (x, y, w, h) = cv2.boundingRect(c)
            if y > addPixel:
                y = y - addPixel
            else:
                y = 0
            if x > addPixel:
                x = x - addPixel
            else:
                x = 0
            temp = bgr_thresh[y:y + h + (addPixel * 2),
                              x:x + w + (addPixel * 2)]
 
            characters.append(temp)
             
        return characters
    else:
        return None

print("✓ Helper functions ready")

class PlateFinder:
    """
    Detects license plates in images using multiple detection strategies
    """
    def __init__(self, minPlateArea, maxPlateArea):
        self.min_area = minPlateArea
        self.max_area = maxPlateArea 
        self.element_structure = cv2.getStructuringElement(
                              shape = cv2.MORPH_RECT, ksize =(22, 3))
 
    def preprocess(self, input_img):
        """Preprocess image using multiple techniques"""
        # Convert to grayscale
        if len(input_img.shape) == 3:
            gray = cv2.cvtColor(input_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = input_img
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply Canny edge detection
        edges = cv2.Canny(filtered, 50, 150)
        
        # Thresholding
        ret, thresh = cv2.threshold(filtered, 127, 255, cv2.THRESH_BINARY)
        
        # Combine methods
        combined = cv2.bitwise_or(edges, thresh)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 9))
        morph = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel, iterations=1)
         
        return morph
 
    def extract_contours(self, after_preprocess):
        """Extract contours from preprocessed image"""
        contours, _ = cv2.findContours(after_preprocess,
                                          mode = cv2.RETR_TREE,
                                          method = cv2.CHAIN_APPROX_SIMPLE)
        return contours
 
    def clean_plate(self, plate):
        """Clean and extract plate region"""
        if len(plate.shape) == 3:
            gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate
            
        thresh = cv2.adaptiveThreshold(gray, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
         
        contours, _ = cv2.findContours(thresh.copy(),
                                          cv2.RETR_EXTERNAL,
                                          cv2.CHAIN_APPROX_SIMPLE)
 
        if contours:
            areas = [cv2.contourArea(c) for c in contours]
            max_index = np.argmax(areas) 
            max_cnt = contours[max_index]
            max_cntArea = areas[max_index]
            x, y, w, h = cv2.boundingRect(max_cnt)
            
            if not self.ratioCheck(max_cntArea, plate.shape[1], plate.shape[0]):
                return plate, False, None
             
            return plate, True, [x, y, w, h]
        else:
            return plate, False, None
 
    def check_plate(self, input_img, contour):
        """Check if contour is a valid plate"""
        x, y, w, h = cv2.boundingRect(contour)
        aspect = float(w) / h if h != 0 else 0
        
        # Check aspect ratio (license plates are wider than tall)
        if aspect < 2.0 or aspect > 8.0:
            return None, None, None
        
        # Check minimum size
        if w < 20 or h < 10:
            return None, None, None
            
        # Ensure boundaries are valid
        x = max(0, x)
        y = max(0, y)
        w = min(w, input_img.shape[1] - x)
        h = min(h, input_img.shape[0] - y)
        
        if w <= 0 or h <= 0:
            return None, None, None
        
        try:
            after_validation_img = input_img[y:y + h, x:x + w]
            coordinates = (x, y)

            # Attempt to segment characters inside the candidate plate region.
            # If segmentation fails, we still keep the full plate image for Tesseract OCR.
            characters_on_plate = self.find_characters_on_plate(after_validation_img)
            if characters_on_plate is not None and len(characters_on_plate) >= 4:
                return after_validation_img, characters_on_plate, coordinates

            return after_validation_img, None, coordinates
        except Exception:
            pass
         
        return None, None, None
 
    def find_possible_plates(self, input_img):
        """Find all possible license plates in image"""
        plates = []
        self.char_on_plate = []
        self.corresponding_area = []
 
        self.after_preprocess = self.preprocess(input_img)
        possible_plate_contours = self.extract_contours(self.after_preprocess)
 
        # Filter by area and aspect ratio first
        # This reduces false positives before OCR is attempted.
        valid_contours = []
        for cnt in possible_plate_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = float(w) / h if h != 0 else 0
            area = w * h
            
            # More relaxed criteria
            if 2 < aspect < 8 and 200 < area < 50000:
                valid_contours.append(cnt)
        
        # Process valid contours
        for cnts in valid_contours:
            plate, characters_on_plate, coordinates = self.check_plate(input_img, cnts)
             
            if plate is not None:
                plates.append(plate)
                self.char_on_plate.append(characters_on_plate)
                self.corresponding_area.append(coordinates)
 
        return plates if len(plates) > 0 else None
 
    def find_characters_on_plate(self, plate):
        """Find characters on plate"""
        charactersFound = segment_chars(plate, 400)
        return charactersFound if charactersFound else None
 
    def ratioCheck(self, area, width, height):
        """Check if area ratio is valid for a plate"""
        min_area = self.min_area
        max_area = self.max_area
        ratioMin = 2.5
        ratioMax = 7.0
 
        ratio = float(width) / float(height) if height != 0 else 0
         
        if ratio < 1:
            ratio = 1 / ratio if ratio != 0 else 0
         
        if (area < min_area or area > max_area) or (ratio < ratioMin or ratio > ratioMax):
            return False
         
        return True
 
    def preRatioCheck(self, area, width, height):
        """Pre-check ratio for candidate plates"""
        min_area = self.min_area
        max_area = self.max_area
        ratioMin = 2.0
        ratioMax = 8.0
 
        ratio = float(width) / float(height) if height != 0 else 0
         
        if ratio < 1:
            ratio = 1 / ratio if ratio != 0 else 0
 
        if (area < min_area or area > max_area) or (ratio < ratioMin or ratio > ratioMax):
            return False
         
        return True
 
    def validateRatio(self, rect):
        """Validate plate ratio"""
        (x, y), (width, height), rect_angle = rect
 
        if (width > height):
            angle = -rect_angle
        else:
            angle = 90 + rect_angle
 
        if angle > 25:
            return False
         
        if (height == 0 or width == 0):
            return False
 
        area = width * height
         
        if not self.preRatioCheck(area, width, height):
            return False
        else:
            return True

class OCR:
    """
    Optical Character Recognition using Tesseract.
    Uses pytesseract to read alphanumeric plate characters.
    """
    def __init__(self, tesseract_cmd=None):
        """Initialize the Tesseract OCR engine."""
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
        self.char_config = r"--psm 10 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        self.plate_config = r"--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        self.frame_text_config = r"--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        self.whitelist_pattern = re.compile(r"[^A-Z0-9]")

        print(f"✓ OCR initialized using Tesseract at: {self.tesseract_cmd}")

    def preprocess_char(self, image):
        """Prepare a single character image for Tesseract."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        gray = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh = cv2.bitwise_not(thresh)
        return thresh

    def preprocess_plate(self, image):
        """Prepare a full plate image for fallback recognition."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        gray = cv2.resize(gray, (400, 100), interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def _clean_text(self, text):
        text = text.upper().strip()
        return self.whitelist_pattern.sub("", text)

    def label_image(self, image):
        """Recognize a single character image."""
        try:
            prep = self.preprocess_char(image)
            text = pytesseract.image_to_string(prep, config=self.char_config)
            text = self._clean_text(text)
            return text if text else "?"
        except Exception:
            return "?"

    def label_plate(self, image):
        """Recognize a full license plate image as fallback."""
        try:
            prep = self.preprocess_plate(image)
            text = pytesseract.image_to_string(prep, config=self.plate_config)
            text = self._clean_text(text)
            return text if text else "?"
        except Exception:
            return "?"

    def label_image_list(self, listImages, imageSizeOutput=None):
        """Recognize a list of segmented character images."""
        if not listImages:
            return "", 0

        plate = ""
        for img in listImages:
            char = self.label_image(img)
            if char and char != "?":
                plate += char

        return plate, len(plate)

    def detect_plate_texts(self, image):
        """Detect candidate plate-like text strings in a full image."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Use full-frame OCR as a fallback path when plate candidates are
        # missed or segmentation does not provide a clean character set.
        data = pytesseract.image_to_data(
            gray,
            config=self.frame_text_config,
            output_type=pytesseract.Output.DICT,
        )

        detected = []
        for i, text in enumerate(data['text']):
            clean = self._clean_text(text)
            conf = -1
            try:
                conf = int(data['conf'][i])
            except Exception:
                pass

            # Only keep reasonably confident plate-like text strings.
            if 4 <= len(clean) <= 8 and any(ch.isdigit() for ch in clean) and conf > 30:
                if clean not in detected:
                    detected.append(clean)

        return detected

print("✓ OCR class ready")

# Initialize the detector and recognizer
# PlateFinder controls the plate candidate size range.
# Tesseract OCR is used for text recognition instead of a TensorFlow model.
plate_finder = PlateFinder(100, 50000)

print("Loading Tesseract OCR...")
ocr = OCR()
print("✓ OCR engine loaded successfully")

def process_video(video_path, max_frames=200, frame_skip=5):
    """
    Process video and detect license plates.
    
    Args:
        video_path: Path to local video file or URL
        max_frames: Maximum frames to process
        frame_skip: Process every nth frame (for speed)
    """
    print(f"\n{'='*70}")
    print(f"  LICENSE PLATE DETECTION SYSTEM")
    print(f"{'='*70}")
    print(f"\nProcessing video: {video_path}")
    
    # Get video file path
    if video_path.startswith('http://') or video_path.startswith('https://'):
        print("Downloading video...")
        local_path = "/tmp/license_plate_video.mp4"
        response = requests.get(video_path, stream=True)
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        video_path = local_path
        print(f"✓ Video downloaded\n")
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"❌ Error: Could not open video file: {video_path}")
        return None
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"VIDEO INFORMATION:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Total Frames: {total_frames}")
    print(f"  Duration: {total_frames/fps:.2f} seconds")
    print(f"\nScanning video for license plates...")
    print(f"{'='*70}\n")
    
    detected_plates = []
    processed_frames = 0
    actual_frame_count = 0
    frames_with_plates = 0
    
    try:
        while cap.isOpened() and processed_frames < max_frames:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            actual_frame_count += 1
            
            # Skip frames
            if actual_frame_count % frame_skip != 0:
                continue
            
            processed_frames += 1
            
            # Resize frame for faster processing
            frame_resized = cv2.resize(frame, (640, 480))
            
            # Find plates
            plates = plate_finder.find_possible_plates(frame_resized)
            
            if plates:
                frames_with_plates += 1
                print(f"Frame {actual_frame_count}: ✓ Detected {len(plates)} plate(s)")
                
                # Process each plate
                for idx, plate in enumerate(plates):
                    try:
                        # Get characters for this plate
                        if hasattr(plate_finder, 'char_on_plate') and len(plate_finder.char_on_plate) > idx:
                            characters = plate_finder.char_on_plate[idx]
                        else:
                            characters = None
                        
                        # If segmentation succeeded, try character-by-character OCR first
                        if characters:
                            plate_text, length = ocr.label_image_list(characters, 128)
                        else:
                            plate_text, length = "", 0

                        # If character segmentation failed or result is too short, read the whole plate region
                        if length < 4:
                            plate_text = ocr.label_plate(plate)
                            length = len(plate_text)

                        if plate_text and length > 0 and plate_text != "?":
                            if plate_text not in detected_plates:
                                detected_plates.append(plate_text)
                                print(f"    └─ Plate: {plate_text}")
                    except Exception:
                        pass

            # Fallback: detect plate-like text in the whole frame if no region OCR succeeded
            # This helps catch plates when detection boxes are too loose or missing.
            fallback_texts = ocr.detect_plate_texts(frame_resized)
            for text in fallback_texts:
                if text not in detected_plates:
                    detected_plates.append(text)
                    print(f"Frame {actual_frame_count}: ✓ Fallback detected plate-like text: {text}")
    except Exception as e:
        print(f"❌ Error while processing frames: {e}")
    finally:
        cap.release()

    # Summary
    print(f"\n{'='*70}")
    print(f"  PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"Summary:")
    print(f"  Total Frames Processed: {actual_frame_count}")
    print(f"  Frames Analyzed: {processed_frames}")
    print(f"  Frames with Detections: {frames_with_plates}")
    print(f"  Total Plates Identified: {len(detected_plates)}")
    
    if detected_plates:
        print(f"\n  DETECTED LICENSE PLATES:")
        print(f"  {'-'*66}")
        for i, plate in enumerate(detected_plates, 1):
            print(f"  {i}. {plate}")
        print(f"  {'-'*66}")
    else:
        print("\n  No plates detected in this video")
    
    print(f"\n{'='*70}\n")
    
    return detected_plates

print("✓ Video processing function ready")

# Debug: Extract and analyze a frame from the video
video_path = "/home/mayanja/Downloads/License Plate Detection Test.mp4"

cap = cv2.VideoCapture(video_path)
frame_count = 0

print("Extracting frames for analysis...")
test_frames = []

while cap.isOpened() and len(test_frames) < 5:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    if frame_count % 100 == 0:  # Sample every 100 frames
        test_frames.append(frame.copy())

cap.release()

print(f"Extracted {len(test_frames)} test frames")

# Test plate detection on first frame
if test_frames:
    test_frame = test_frames[0]
    print(f"\nTesting detection on frame shape: {test_frame.shape}")
    
    # Resize for processing
    resized = cv2.resize(test_frame, (640, 480))
    
    # Preprocess to see what we're detecting
    preprocessed = plate_finder.preprocess(resized)
    
    # Find contours
    contours = plate_finder.extract_contours(preprocessed)
    print(f"Found {len(contours)} contours in preprocessed image")
    
    if len(contours) > 0:
        area_list = [cv2.contourArea(c) for c in contours]
        print(f"Contour areas: min={min(area_list)}, max={max(area_list)}, count={len(area_list)}")
        print(f"Top 5 contour areas: {sorted(area_list, reverse=True)[:5]}")
    
    # Try direct plate detection
    plates = plate_finder.find_possible_plates(resized)
    if plates:
        print(f"✓ Found {len(plates)} plates!")
    else:
        print("No plates found - may need further tuning")

# Test with the License Plate Detection Test video
test_video = "/home/mayanja/Downloads/Licence Plate Camera Illustration Video.mp4"

# Check if file exists
if os.path.exists(test_video):
    print(f"✓ Test video found: {test_video}")
    results = process_video(test_video, max_frames=300, frame_skip=3)
else:
    print(f"❌ Test video not found at: {test_video}")
    print("\nAvailable videos in Downloads:")
    import glob
    videos = glob.glob("/home/mayanja/Downloads/*.mp4") + glob.glob("/home/mayanja/Downloads/*.avi")
    for v in videos[:5]:
        print(f"  - {v}")




# Streamlit App
st.title("License Plate Detection System")

st.write("Upload a video to detect license plates using OpenCV and Tesseract OCR.")

uploaded_file = st.file_uploader("Choose a video file", type=["mp4", "avi", "mov"])

if uploaded_file is not None:
    # Save uploaded file to temp
    temp_path = "temp_video.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.video(uploaded_file)
    
    if st.button("Process Video"):
        with st.spinner("Processing video... This may take a few minutes."):
            results = process_video(temp_path, max_frames=100, frame_skip=5)
        
        st.success("Processing complete!")
        st.write("Detected License Plates:")
        if results:
            for plate in results:
                st.write(f"- {plate}")
        else:
            st.write("No plates detected.")
        
        # Clean up
        os.remove(temp_path)
