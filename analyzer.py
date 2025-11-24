import math
import time
from collections import deque
from config import BAD_POSTURE_THRESHOLD_SECONDS

class PostureAnalyzer:
    def __init__(self):
        # Thresholds
        self.neck_angle_threshold = 30
        self.shoulder_alignment_threshold = 10
        self.spine_curvature_threshold = 15
        
        # --- NEW: Smoothing Buffers for Accuracy ---
        # We store the last 10 frames of data to average them out.
        # This prevents "jitter" from triggering false alerts.
        self.buffer_size = 10
        self.neck_buffer = deque(maxlen=self.buffer_size)
        self.shoulder_buffer = deque(maxlen=self.buffer_size)
        self.spine_buffer = deque(maxlen=self.buffer_size)
        
        # State Tracking
        self.bad_posture_start_time = None
        self.is_bad_posture = False
        self.bad_posture_duration = 0
        
        self.good_posture_seconds = 0
        self.bad_posture_seconds = 0
        self.last_update_time = time.time()
    
    def calculate_angle(self, point1, point2, point3):
        """Calculate the angle between three points (in degrees)"""
        if not all([point1, point2, point3]):
            return None
            
        v1 = {'x': point1['x'] - point2['x'], 'y': point1['y'] - point2['y']}
        v2 = {'x': point3['x'] - point2['x'], 'y': point3['y'] - point2['y']}
        
        dot_product = v1['x'] * v2['x'] + v1['y'] * v2['y']
        mag1 = math.sqrt(v1['x']**2 + v1['y']**2)
        mag2 = math.sqrt(v2['x']**2 + v2['y']**2)
        
        if mag1 * mag2 == 0:
            return None
            
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(min(cos_angle, 1.0), -1.0)
        angle_rad = math.acos(cos_angle)
        return math.degrees(angle_rad)

    def _get_smoothed_angle(self, buffer, new_value):
        """Adds new value to buffer and returns the average."""
        if new_value is not None:
            buffer.append(new_value)
        
        if not buffer:
            return None
            
        return sum(buffer) / len(buffer)

    def _evaluate_component(self, angle, threshold_check_func, fail_message):
        """
        Returns: (is_valid, is_passing, feedback_message)
        """
        if angle is None:
            return False, None, None
            
        is_passing = threshold_check_func(angle)
        message = None if is_passing else fail_message
        return True, is_passing, message

    def analyze_posture(self, key_points):
        if not key_points:
            self.last_update_time = time.time()
            return {
                'is_good_posture': False, 
                'status': 'No Person Detected',
                'feedback_messages': []
            }
        
        # --- 1. Calculate Raw Angles ---
        raw_neck = self.calculate_angle(key_points.get('nose'), key_points.get('left_shoulder'), key_points.get('left_hip'))
        raw_shoulder = self.calculate_angle(key_points.get('left_shoulder'), key_points.get('right_shoulder'), key_points.get('nose'))
        raw_spine = self.calculate_angle(key_points.get('left_shoulder'), key_points.get('left_hip'), key_points.get('left_knee'))

        # --- 2. Smooth Angles (Increases Accuracy) ---
        # [Image of moving average smoothing graph]

        # This removes sudden spikes in data caused by webcam noise
        neck_angle = self._get_smoothed_angle(self.neck_buffer, raw_neck)
        shoulder_alignment = self._get_smoothed_angle(self.shoulder_buffer, raw_shoulder)
        spine_curvature = self._get_smoothed_angle(self.spine_buffer, raw_spine)

        # --- 3. Evaluate Specific Components ---
        results = []
        feedback_messages = []

        # Check Neck
        valid, passing, msg = self._evaluate_component(
            neck_angle, 
            lambda a: a > (90 - self.neck_angle_threshold),
            "Keep head straight"
        )
        if valid: 
            results.append(passing)
            if msg: feedback_messages.append(msg)

        # Check Shoulders
        valid, passing, msg = self._evaluate_component(
            shoulder_alignment, 
            lambda a: abs(180 - a) < self.shoulder_alignment_threshold,
            "Level your shoulders" 
        )
        if valid: 
            results.append(passing)
            if msg: feedback_messages.append(msg)

        # Check Spine
        valid, passing, msg = self._evaluate_component(
            spine_curvature, 
            lambda a: a > (180 - self.spine_curvature_threshold),
            "Straighten your back"
        )
        if valid: 
            results.append(passing)
            if msg: feedback_messages.append(msg)

        # --- 4. Determine State ---
        current_time = time.time()
        time_delta = current_time - self.last_update_time
        self.last_update_time = current_time

        if not results:
            return {
                'is_good_posture': False,
                'status': 'Undetected',
                'feedback_messages': ["User not detected"]
            }

        is_good_posture = all(results)

        # --- 5. Update Stats ---
        if is_good_posture:
            self.good_posture_seconds += time_delta
            if self.bad_posture_start_time:
                self.bad_posture_duration = current_time - self.bad_posture_start_time
                self.bad_posture_start_time = None
                self.is_bad_posture = False
        else:
            self.bad_posture_seconds += time_delta
            if not self.bad_posture_start_time:
                self.bad_posture_start_time = current_time
                self.is_bad_posture = True
            else:
                self.bad_posture_duration = current_time - self.bad_posture_start_time

        return {
            'neck_angle': neck_angle,
            'shoulder_alignment': shoulder_alignment,
            'spine_curvature': spine_curvature,
            'is_good_posture': is_good_posture,
            'status': 'Active',
            'bad_posture_duration': self.bad_posture_duration,
            'feedback_messages': feedback_messages  # <--- Now returns list of specific issues
        }

    # ... (Keep other methods like should_trigger_alert, reset_stats the same) ...
    def should_trigger_alert(self):
        return self.bad_posture_duration >= BAD_POSTURE_THRESHOLD_SECONDS

    def reset_bad_posture_timer(self):
        self.bad_posture_start_time = None
        self.bad_posture_duration = 0
        self.is_bad_posture = False

    def get_posture_stats(self):
        return {
            'good_posture_seconds': self.good_posture_seconds,
            'bad_posture_seconds': self.bad_posture_seconds,
            'bad_posture_duration': self.bad_posture_duration,
            'is_bad_posture': self.is_bad_posture
        }
    
    def reset_stats(self):
        self.good_posture_seconds = 0
        self.bad_posture_seconds = 0
        self.bad_posture_duration = 0
        self.bad_posture_start_time = None
        self.is_bad_posture = False
        self.last_update_time = time.time()
        # Clear buffers
        self.neck_buffer.clear()
        self.shoulder_buffer.clear()
        self.spine_buffer.clear()