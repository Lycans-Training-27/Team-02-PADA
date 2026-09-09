#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from mavros_msgs.srv import SetMode
from mavros_msgs.msg import State

class PADAValidationProtocol(Node):
    def __init__(self):
        super().__init__('pada_validation_protocol_node')
        
        self.current_state = "NORMAL_FLIGHT"
        self.glitch_counter = 0
        self.glitch_threshold = 3 

        self.mavros_state_sub = self.create_subscription(
            State, '/mavros/state', self.mavros_state_callback, 10)
        self.vision_sub = self.create_subscription(
            String, '/pada/vision/detection', self.vision_callback, 10)
        
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')
        self.get_logger().info("PADA 5.2.5 Validation Node Initialized.")

    def mavros_state_callback(self, msg):
        self.connected = msg.connected
        self.current_mavros_mode = msg.mode

    def vision_callback(self, msg):
        detection = msg.data.lower()

        # State 4: Handling Glitches & Confusion (Debounce Filter)
        if "blurry" in detection or "partial" in detection or "unknown" in detection:
            self.glitch_counter += 1
            if self.glitch_counter < self.glitch_threshold:
                self.get_logger().warn(f"Glitch detected! Filter active ({self.glitch_counter}/{self.glitch_threshold}).")
                return
            else:
                self.get_logger().error("Persistent noise! Triggering Hold mode.")
                self.set_flight_mode("HOLD")
                return

        self.glitch_counter = 0

        # State 2: Hazard Avoidance & Recovery
        if "hazard" in detection:
            self.get_logger().info("HAZARD DETECTED! Executing safe steering.")
            self.current_state = "HAZARD_AVOIDANCE"
            self.set_flight_mode("GUIDED")

        # State 3: Visual Command Processing
        elif "cmd_rtl" in detection:
            self.get_logger().info("VISUAL COMMAND: RTL Triggered.")
            self.current_state = "VISUAL_COMMAND"
            self.set_flight_mode("RTL")

        elif "cmd_land" in detection:
            self.get_logger().info("VISUAL COMMAND: LAND Triggered.")
            self.current_state = "VISUAL_COMMAND"
            self.set_flight_mode("LAND")

        # State 1: Normal Flight
        else:
            if self.current_state != "NORMAL_FLIGHT":
                self.get_logger().info("Hazard cleared. Resuming AUTO Mission.")
                self.current_state = "NORMAL_FLIGHT"
                self.set_flight_mode("AUTO")

    def set_flight_mode(self, custom_mode):
        if not self.set_mode_client.wait_for_service(timeout_sec=1.0):
            return
        req = SetMode.Request()
        req.custom_mode = custom_mode
        self.set_mode_client.call_async(req)

def main(args=None):
    rclpy.init(args=args)
    node = PADAValidationProtocol()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

