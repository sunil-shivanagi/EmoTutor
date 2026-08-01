import cv2
import json
import torch
import numpy as np
import mediapipe as mp
import torchvision.models as models
import torch.nn as nn

from torchvision import transforms
from PIL import Image

# ----------------------------
# LOAD CONFIG
# ----------------------------
with open("app/models/config.json", "r") as f:
    config = json.load(f)

CLASSES = config["classes"]   # ["Positive", "Negative"]

# ----------------------------
# LOAD MODEL (ResNet18)
# ----------------------------
device = torch.device("cpu")

model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, 2)

model.load_state_dict(
    torch.load("app/models/final_emotion.pth", map_location=device)
)

model.eval()

# ----------------------------
# MEDIAPIPE FACE MESH
# ----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1
)

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# ----------------------------
# IMAGE TRANSFORM
# Must match training
# ----------------------------
transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

# ----------------------------
# EAR CALCULATION
# ----------------------------
def eye_aspect_ratio(landmarks, eye_indices, w, h):
    points = []

    for idx in eye_indices:
        x = int(landmarks[idx].x * w)
        y = int(landmarks[idx].y * h)
        points.append((x, y))

    v1 = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
    v2 = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
    h_dist = np.linalg.norm(np.array(points[0]) - np.array(points[3]))

    if h_dist == 0:
        return 0

    return (v1 + v2) / (2.0 * h_dist)

# ----------------------------
# MAIN FUNCTION
# ----------------------------
def detect_emotion(frame_bytes):
    npimg = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return "No Face"

    h, w, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    # No face detected
    if not results.multi_face_landmarks:
        return "No Face"

    landmarks = results.multi_face_landmarks[0].landmark

    # ----------------------------
    # DROWSINESS CHECK
    # ----------------------------
    left_ear = eye_aspect_ratio(landmarks, LEFT_EYE, w, h)
    right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE, w, h)
    ear = min(left_ear, right_ear)

    if ear < 0.15:
        return "Drowsy"

    # ----------------------------
    # EMOTION DETECTION
    # ----------------------------
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_img = Image.fromarray(gray)

    img_tensor = transform(face_img).unsqueeze(0)

    with torch.no_grad():
        output = model(img_tensor)
        pred = torch.argmax(output, dim=1).item()

    return CLASSES[pred]