import cv2
import mediapipe as mp
from config import POSE_DETECTION_CONFIDENCE, POSE_TRACKING_CONFIDENCE

class MediaPipePoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Initialize MediaPipe Pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=POSE_DETECTION_CONFIDENCE,
            min_tracking_confidence=POSE_TRACKING_CONFIDENCE,
            model_complexity=1
        )
        
        # Define landmark names mapping for easy lookup
        self.landmark_names = {
            0: 'nose',
            1: 'left_eye_inner', 2: 'left_eye', 3: 'left_eye_outer',
            4: 'right_eye_inner', 5: 'right_eye', 6: 'right_eye_outer',
            7: 'left_ear', 8: 'right_ear',
            9: 'mouth_left', 10: 'mouth_right',
            11: 'left_shoulder', 12: 'right_shoulder',
            13: 'left_elbow', 14: 'right_elbow',
            15: 'left_wrist', 16: 'right_wrist',
            17: 'left_pinky', 18: 'right_pinky',
            19: 'left_index', 20: 'right_index',
            21: 'left_thumb', 22: 'right_thumb',
            23: 'left_hip', 24: 'right_hip',
            25: 'left_knee', 26: 'right_knee',
            27: 'left_ankle', 28: 'right_ankle',
            29: 'left_heel', 30: 'right_heel',
            31: 'left_foot_index', 32: 'right_foot_index'
        }
    
    def detect(self, frame):
        """
        Main function called by UI.
        1. Detects pose
        2. Draws skeleton on frame (in-place)
        3. Returns dictionary of keypoints
        """
        # Convert to RGB for MediaPipe 
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False # Optimization
        
        results = self.pose.process(rgb_frame)
        
        if not results.pose_landmarks:
            return None
            
        # 1. Draw Landmarks on the frame (User Feedback)
        # We draw on the original BGR frame
        self.mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
        # 2. Convert to Keypoints Dictionary
        key_points = {}
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            name = self.landmark_names.get(idx)
            if name:
                key_points[name] = {
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }
                
        return key_points
    
    def close(self):
        self.pose.close()