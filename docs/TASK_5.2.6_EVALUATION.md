# Task 5.2.6: Evaluation Matrix & Architecture Defense

## 1. Functional Requirements Compliance
* **Vision-to-SITL Bridge:** Real-time ROS 2 node (`pada_validation_protocol.py`) listening to `/pada/vision/detection` and interfacing directly with MAVROS services (`/mavros/set_mode`).
* **Closed-loop Flight Control:** 
  * **Hazard Detected:** Automates mode switch from `AUTO` to `GUIDED` for evasive steering.
  * **Clear Area:** Automatically restores `AUTO` mode to resume QGroundControl mission plan.
  * **Visual Commands:** Direct decoding to safety modes (`RTL` / `LAND`).

## 2. Engineering Quality & System Design
* **Glitch & Noise Filtering:** Implemented a debounce counter (`glitch_threshold = 3`). Transient false detections, blurry frames, or partial occlusions are suppressed to ensure flight stability without false mode switches.
* **Error Handling & Resilience:** Built-in safeguards for MAVROS service unavailability using async service calls (`call_async`) and non-blocking status logging.
* **Modular ROS 2 Architecture:** Clean separation between Computer Vision detection nodes and Flight Mode decision logic.

## 3. Trade-off Analysis Matrix

| Metric | System Choice | Rationale & Safety Trade-off |
| :--- | :--- | :--- |
| **Detection Speed vs. Accuracy** | Debounce Filter (3-frame threshold) | Adds a minimal ~100ms delay to eliminate false positives, prioritizing UAV flight safety over instant unsafe triggers. |
| **Control Interface** | MAVROS Mode Switching | Uses native ArduPilot flight modes (`GUIDED`, `AUTO`, `RTL`) rather than raw pitch/roll overrides to ensure the Flight Controller's internal EKF safety stays active. |
| **Frame Drop Handling** | Hold Current State | If vision frames are dropped or corrupted, the system maintains its current stable mode instead of making erratic path changes. |

## 4. Technical Panel Defense (Q&A Strategy)
* **Q: Why not use direct velocity control for hazard avoidance?**
  * *A:* Switching to MAVROS `GUIDED` mode lets ArduPilot's internal navigation stack handle low-level stabilization while we command the higher-level trajectory, ensuring maximum flight safety.
* **Q: How does the system handle rapid camera blur during aggressive maneuvers?**
  * *A:* The glitch filter holds state until stable detections resume for 3 consecutive frames, preventing erratic mode switching.
