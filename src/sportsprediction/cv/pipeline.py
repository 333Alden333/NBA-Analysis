"""Computer Vision pipeline for NBA player tracking and analysis.

CV-01: YOLO-based player detection from game footage
CV-02: ByteTrack player tracking across frames  
CV-03: Movement feature extraction (distance, speed, court zone heatmaps)
CV-04: CV features fed into prediction models

Hardware: 2x NVIDIA GTX 1080 (8GB VRAM each)
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class BoundingBox:
    """Detected player bounding box."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int


@dataclass
class Tracklet:
    """Tracked player across frames."""
    track_id: int
    player_id: Optional[int]  # Mapped to NBA player ID if identified
    positions: list[tuple[float, float]]  # Center positions over time
    velocities: list[tuple[float, float]]  # Movement vectors
    timestamps: list[float]
    jersey_number: Optional[str]
    team_color: Optional[str]


@dataclass
class MovementFeatures:
    """Extracted movement features for a player."""
    total_distance: float  # Total distance traveled (feet)
    avg_speed: float  # Average speed (feet/second)
    max_speed: float  # Peak speed
    time_in_paint: float  # Seconds in paint area
    time_on_perimeter: float  # Seconds outside paint
    transition_count: int  # Number of paint<->perimeter transitions
    avg_distance_from_hoop: float
    heatmap: np.ndarray  # Court zone density


class PlayerDetector:
    """YOLO-based player detection from video frames."""
    
    def __init__(self, model_path: str = "yolov8n"):
        """Initialize YOLO model.
        
        Args:
            model_path: YOLO model variant (yolov8n, yolov8s, yolov8m)
        """
        # Lazy import to avoid dependency issues if not installed
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.available = True
        except ImportError:
            self.model = None
            self.available = False
    
    def detect(self, frame: np.ndarray) -> list[BoundingBox]:
        """Detect players in a single frame.
        
        Args:
            frame: Video frame as numpy array (H, W, 3)
            
        Returns:
            List of detected player bounding boxes
        """
        if not self.available:
            raise RuntimeError("YOLO not installed: pip install ultralytics")
        
        results = self.model(frame, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Assume class 0 is person/player
                if box.cls[0] == 0:  # person class
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    detections.append(BoundingBox(
                        x1=x1, y1=y1, x2=x2, y2=y2,
                        confidence=conf,
                        class_id=int(box.cls[0])
                    ))
        
        return detections


class PlayerTracker:
    """ByteTrack-based multi-object tracking for players."""
    
    def __init__(self):
        """Initialize ByteTrack tracker."""
        try:
            # ByteTrack import - may vary by version
            from bytetracker import ByteTracker
            self.tracker = ByteTracker(
                track_thresh=0.5,
                track_buffer=30,
                match_thresh=0.8
            )
            self.available = True
        except ImportError:
            self.tracker = None
            self.available = False
    
    def update(
        self, 
        detections: list[BoundingBox], 
        frame_idx: int,
        timestamp: float
    ) -> list[Tracklet]:
        """Update tracker with new detections.
        
        Args:
            detections: List of bounding box detections
            frame_idx: Current frame index
            timestamp: Current timestamp in seconds
            
        Returns:
            List of active tracklets
        """
        if not self.available:
            # Simple fallback: create tracklets from detections
            return self._simple_track(detections, frame_idx, timestamp)
        
        # Convert to ByteTrack format
        # Note: This is pseudocode - actual implementation depends on 
        # ByteTrack's specific API
        raise NotImplementedError("ByteTrack integration needs actual implementation")
    
    def _simple_track(
        self,
        detections: list[BoundingBox],
        frame_idx: int,
        timestamp: float
    ) -> list[Tracklet]:
        """Simple fallback tracking without ByteTrack."""
        tracklets = []
        for i, det in enumerate(detections):
            center_x = (det.x1 + det.x2) / 2
            center_y = (det.y1 + det.y2) / 2
            
            tracklets.append(Tracklet(
                track_id=i,
                player_id=None,
                positions=[(center_x, center_y)],
                velocities=[(0.0, 0.0)],
                timestamps=[timestamp],
                jersey_number=None,
                team_color=None
            ))
        return tracklets


class MovementAnalyzer:
    """Extract movement features from tracked player trajectories."""
    
    # Court dimensions (feet)
    COURT_LENGTH = 94
    COURT_WIDTH = 50
    PAINT_WIDTH = 16
    PAINT_LENGTH = 19
    
    def __init__(self, pixels_per_foot: float = 10.0):
        """Initialize movement analyzer.
        
        Args:
            pixels_per_foot: Conversion factor from pixels to feet
        """
        self.ppf = pixels_per_foot
    
    def extract_features(self, tracklet: Tracklet) -> MovementFeatures:
        """Extract movement features from a tracklet.
        
        Args:
            tracklet: Tracked player positions over time
            
        Returns:
            Extracted movement features
        """
        if len(tracklet.positions) < 2:
            return MovementFeatures(
                total_distance=0.0,
                avg_speed=0.0,
                max_speed=0.0,
                time_in_paint=0.0,
                time_on_perimeter=0.0,
                transition_count=0,
                avg_distance_from_hoop=0.0,
                heatmap=np.zeros((10, 10))
            )
        
        positions = np.array(tracklet.positions)
        timestamps = np.array(tracklet.timestamps)
        
        # Calculate distances between consecutive positions
        deltas = np.diff(positions, axis=0)
        distances_pixels = np.sqrt(np.sum(deltas ** 2, axis=1))
        distances_feet = distances_pixels / self.ppf
        
        # Total distance
        total_distance = np.sum(distances_feet)
        
        # Time deltas
        time_deltas = np.diff(timestamps)
        
        # Speeds (feet per second)
        speeds = distances_feet / np.maximum(time_deltas, 0.01)
        
        avg_speed = np.mean(speeds) if len(speeds) > 0 else 0.0
        max_speed = np.max(speeds) if len(speeds) > 0 else 0.0
        
        # Court zone analysis
        in_paint = self._is_in_paint(positions)
        time_in_paint = np.sum(time_deltas[in_paint[:-1]]) if np.any(in_paint) else 0.0
        time_on_perimeter = np.sum(time_deltas[~in_paint[:-1]]) if np.any(~in_paint) else 0.0
        
        # Count transitions
        transitions = np.sum(np.diff(in_paint.astype(int)) != 0)
        
        # Distance from hoop (assume hoop at center for now)
        hoop_pos = np.array([self.COURT_LENGTH / 2, self.COURT_WIDTH / 2])
        distances_from_hoop = np.sqrt(np.sum((positions - hoop_pos) ** 2, axis=1))
        avg_distance_from_hoop = np.mean(distances_from_hoop) / self.ppf
        
        # Heatmap
        heatmap = self._create_heatmap(positions)
        
        return MovementFeatures(
            total_distance=total_distance,
            avg_speed=avg_speed,
            max_speed=max_speed,
            time_in_paint=time_in_paint,
            time_on_perimeter=time_on_perimeter,
            transition_count=transitions,
            avg_distance_from_hoop=avg_distance_from_hoop,
            heatmap=heatmap
        )
    
    def _is_in_paint(self, positions: np.ndarray) -> np.ndarray:
        """Determine which positions are in the paint."""
        # Simplified paint detection (assuming baseline view)
        center_x = self.COURT_LENGTH / 2
        paint_left = center_x - self.PAINT_LENGTH / 2
        paint_right = center_x + self.PAINT_LENGTH / 2
        paint_top = 0
        paint_bottom = self.PAINT_WIDTH
        
        in_paint = (
            (positions[:, 0] >= paint_left) &
            (positions[:, 0] <= paint_right) &
            (positions[:, 1] >= paint_top) &
            (positions[:, 1] <= paint_bottom)
        )
        return in_paint
    
    def _create_heatmap(self, positions: np.ndarray) -> np.ndarray:
        """Create court zone heatmap."""
        # Divide court into 10x10 grid
        heatmap = np.zeros((10, 10))
        
        if len(positions) == 0:
            return heatmap
        
        # Convert to grid coordinates
        x_bins = np.clip((positions[:, 0] / self.COURT_LENGTH * 10).astype(int), 0, 9)
        y_bins = np.clip((positions[:, 1] / self.COURT_WIDTH * 10).astype(int), 0, 9)
        
        # Count visits per zone
        for x, y in zip(x_bins, y_bins):
            heatmap[y, x] += 1
        
        # Normalize
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        
        return heatmap


class CVPipeline:
    """End-to-end computer vision pipeline."""
    
    def __init__(self):
        self.detector = PlayerDetector()
        self.tracker = PlayerTracker()
        self.analyzer = MovementAnalyzer()
    
    def process_video(self, video_path: str) -> dict[int, MovementFeatures]:
        """Process a video file and extract player movement features.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict mapping track_id -> MovementFeatures
        """
        # This is a placeholder - actual implementation would:
        # 1. Load video with OpenCV
        # 2. Process frame by frame
        # 3. Run detection + tracking
        # 4. Extract features
        raise NotImplementedError("Video processing needs implementation")
    
    def process_frame(
        self, 
        frame: np.ndarray, 
        frame_idx: int, 
        timestamp: float
    ) -> list[Tracklet]:
        """Process a single frame.
        
        Args:
            frame: Video frame
            frame_idx: Frame index
            timestamp: Timestamp in seconds
            
        Returns:
            List of active tracklets
        """
        detections = self.detector.detect(frame)
        tracklets = self.tracker.update(detections, frame_idx, timestamp)
        return tracklets
