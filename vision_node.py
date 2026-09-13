import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraPublisherNode(Node):
    def __init__(self):
        super().__init__('camera_publisher_node')
        self.publisher_ = self.create_publisher(Image, '/camera/image_raw', 10)
        
        # رابط كاميرا الموبايل (تأكد من مطابقة الـ IP الحالي)
        self.url = "http://192.168.1.4:8080/video"
        self.cap = cv2.VideoCapture(self.url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.bridge = CvBridge()
        self.timer = self.create_timer(0.033, self.timer_callback) # ~30 FPS
        
        if not self.cap.isOpened():
            self.get_logger().error(f"فشل الاتصال بكاميرا الهاتف عبر الرابط: {self.url}")
        else:
            self.get_logger().info("تم الاتصال بكاميرا الموبايل بنجاح وبدء نشر البث على ROS 2!")

    def timer_callback(self):
        if not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return
            
        try:
            frame = cv2.resize(frame, (640, 480))
            msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            self.publisher_.publish(msg)
        except Exception as e:
            pass

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