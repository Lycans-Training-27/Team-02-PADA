import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraPublisherNode(Node):
    def __init__(self):
        super().__init__('camera_publisher_node')
        
        self.publisher_ = self.create_publisher(Image, '/camera/image_raw', 10)
        
        timer_period = 0.033  # ~30 FPS
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        # رابط كاميرا الموبايل (يمكنك تغليفه أو تعديل الـ IP حسب ما يظهر في تطبيق IP Webcam)
        self.url = "http://192.168.1.7:8080/video"
        self.cap = cv2.VideoCapture(self.url)
        
        # تقليل الـ Buffer size الخاص بـ OpenCV لمنع تأخير الإطارات (Lag)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.bridge = CvBridge()
        
        if not self.cap.isOpened():
            self.get_logger().error(f"فشل الاتصال بكاميرا الهاتف عبر الرابط: {self.url}")
        else:
            self.get_logger().info("تم الاتصال بكاميرا الهاتف بنجاح وبدء نشر البث على ROS 2!")

    def timer_callback(self):
        ret, frame = self.cap.read()
        
        # حماية ضد انقطاع الإطارات أو الـ Timeouts لمنع إغراق التيرمينال بالأخطاء
        if not ret or frame is None:
            # نتجاوز الإطار الحالي بهدوء بدلاً من إيقاف العقدة أو طباعة أخطاء مزعجة
            return
            
        # تحويل إطار OpenCV إلى رسالة ROS Image ونشرها
        try:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            self.publisher_.publish(msg)
        except Exception as e:
            self.get_logger().warn(f"خطأ أثناء تحويل ونشر الإطار: {str(e)}")

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CameraPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()