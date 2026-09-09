#!/usr/bin/env python3
import rospy
from mavros_msgs.srv import SetMode, SetModeRequest
from std_msgs.msg import String

class PADAValidationProtocol:
    def __init__(self):
        rospy.init_node('pada_validation_node')

        rospy.wait_for_service('/mavros/set_mode')
        self.set_mode_service = rospy.ServiceProxy('/mavros/set_mode', SetMode)

        rospy.Subscriber('/vision/detection', String, self.vision_callback)

        self.last_signal = None
        self.consecutive_count = 0
        self.REQUIRED_FRAMES = 3 

        rospy.loginfo("[PADA 5.2.5] Validation Protocol Node Active and Ready.")

    def change_flight_mode(self, mode_name):
        try:
            req = SetModeRequest()
            req.custom_mode = mode_name
            res = self.set_mode_service(req)
            if res.mode_sent:
                rospy.loginfo(f"[MAVROS] Mode successfully switched to: {mode_name}")
        except Exception as e:
            rospy.logerr(f"Failed to call MAVROS mode service: {e}")

    def vision_callback(self, msg):
        detection = msg.data.strip()

        if detection == self.last_signal:
            self.consecutive_count += 1
        else:
            self.last_signal = detection
            self.consecutive_count = 1
            return

        if self.consecutive_count < self.REQUIRED_FRAMES:
            return

        if detection == "HAZARD":
            rospy.logwarn("[State 2] Hazard Detected! Switching to GUIDED for avoidance.")
            self.change_flight_mode("GUIDED")

        elif detection == "CLEAR":
            rospy.loginfo("[State 2] Hazard Cleared! Resuming AUTO route.")
            self.change_flight_mode("AUTO")

        elif detection == "CMD_RTL":
            rospy.loginfo("[State 3] Visual Command Decoded: Executing RTL.")
            self.change_flight_mode("RTL")

        elif detection == "CMD_LAND":
            rospy.loginfo("[State 3] Visual Command Decoded: Executing LAND.")
            self.change_flight_mode("LAND")

        elif detection == "NONE":
            pass

if __name__ == '__main__':
    try:
        protocol = PADAValidationProtocol()
        rospy.spin()
    except rospy.ROSInterruptException: pass
