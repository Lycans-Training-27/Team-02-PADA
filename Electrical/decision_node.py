import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
from mavros_msgs.srv import SetMode

class VisionProcessorNode(Node):
    def __init__(self):
        super().__init__('vision_processor_node')
        
        # 1. الاستماع لتوبيك الكاميرا
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.listener_callback,
            10
        )
        
        # 2. عميل MAVROS لتغيير وضع الطيران
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')
        
        self.bridge = CvBridge()
        self.hazard_detected_prev = False
        self.get_logger().info("تم تشغيل عقدة الإدراك المتكاملة (الموقف الأول والثاني) بنجاح...")

    def send_flight_command(self, target_mode):
        """إرسال أمر تغيير وضع الطيران إلى MAVROS ومنه إلى ArduPilot SITL"""
        if self.set_mode_client.wait_for_service(timeout_sec=0.5):
            request = SetMode.Request()
            request.custom_mode = target_mode
            future = self.set_mode_client.call_async(request)
            self.get_logger().info(f"-> [تحديث حالة المهمة]: تم إرسال أمر الطيران إلى وضع: {target_mode}")

    def listener_callback(self, msg):
        try:
            # تحويل رسالة ROS إلى OpenCV BGR
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # --- الموقف الأول: رصد عائق بيئي (Environmental Hazard - اللون الأحمر مثلاً) ---
            lower_red1 = np.array([0, 120, 70])
            upper_red1 = np.array([10, 255, 255])
            mask_hazard = cv2.inRange(hsv, lower_red1, upper_red1)
            hazard_pixels = cv2.countNonZero(mask_hazard)
            
            # --- الموقف الثاني: رصد هدف أوامر (Visual Mission Instruction - اللون الأزرق مثلاً) ---
            lower_blue = np.array([100, 150, 50])
            upper_blue = np.array([140, 255, 255])
            mask_target = cv2.inRange(hsv, lower_blue, upper_blue)
            target_pixels = cv2.countNonZero(mask_target)
            
            threshold_area = 600  # الحد الأدنى لتأكيد الرؤية وتجنب الإنذارات الكاذبة
            
            # تنفيذ منطق الموقف الأول (تفادي العوائق)
            if hazard_pixels > threshold_area:
                if not self.hazard_detected_prev:
                    self.get_logger().warn("⚠️ [الموقف الأول]: تم رصد عائق بيئي في مسار الطيران! تنفيذ مناورة التفادي...")
                    self.send_flight_command("GUIDED")
                    self.hazard_detected_prev = True
            else:
                if self.hazard_detected_prev:
                    self.get_logger().info("✅ [الموقف الأول]: تم تجاوز العائق بنجاح. العودة للمسار الأصلي...")
                    self.send_flight_command("AUTO")
                    self.hazard_detected_prev = False

            # تنفيذ منطق الموقف الثاني (أوامر المهمة البصرية)
            if target_pixels > threshold_area and not self.hazard_detected_prev:
                self.get_logger().info("🎯 [الموقف الثاني]: تم رصد هدف بصري (Target A)!")
                self.send_flight_command("RTL")

            # عرض البث الحي للمراقبة
            cv2.imshow("PADA Dual Scenario Feed (Hazard & Target)", frame)
            cv2.waitKey(1)
            
        except Exception as e:
            self.get_logger().error(f"خطأ أثناء معالجة السيناريو: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = VisionProcessorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()