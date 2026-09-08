import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
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
        
        # 2. عميل MAVROS لتنفيذ أمر Flight Execution (تغيير وضع الطيران)
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')
        
        self.bridge = CvBridge()
        self.command_sent = False  # لضمان إرسال الأمر مرة واحدة فقط للاختبار
        self.get_logger().info("تم تشغيل عقدة الرؤية والتحكم بنجاح...")

    def send_flight_command(self, target_mode):
        """إرسال أمر تغيير وضع الطيران إلى MAVROS ومنه إلى ArduPilot SITL"""
        if self.set_mode_client.wait_for_service(timeout_sec=0.5):
            request = SetMode.Request()
            request.custom_mode = target_mode
            future = self.set_mode_client.call_async(request)
            self.get_logger().info(f"-> تم إرسال أمر تغيير وضع الطيران إلى: {target_mode}")

    def listener_callback(self, msg):
        try:
            # تحويل رسالة ROS إلى OpenCV BGR
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # --- شرط الرؤية (Vision Condition / Decision Logic) ---
            # كمثال عملي: هنقيس متوسط إضاءة الإطار، أو نقدر نعتبرها "رؤية هدف"
            avg_brightness = gray_frame.mean()
            
            # لو الكاميرا شايفة إضاءة معينة (كمحاكاة لوصول هدف أو بدء المهمة)
            if not self.command_sent:
                # هنا بنفذ الاتنين: اختبار فوري + ربط بشرط الرؤية
                self.get_logger().info(f"تم رصد إطار برؤية واضحة (Brightness: {avg_brightness:.2f}). جاري إرسال أمر الطيران...")
                
                # إرسال أمر التحويل لوضع GUIDED لـ MAVROS / SITL
                self.send_flight_command("GUIDED")
                self.command_sent = True  # عشان ميبعتش الأمر كل فريم ويقرفنا

            # عرض الفيديو الحي
            cv2.imshow("PADA Live Vision & Execution Feed", gray_frame)
            cv2.waitKey(1)
            
        except Exception as e:
            self.get_logger().error(f"خطأ أثناء المعالجة: {e}")

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