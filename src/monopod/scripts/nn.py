#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
 
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory 
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration

from sensor_msgs.msg import JointState  #sensor_msgs/msg/JointState
from sensor_msgs.msg import Imu
import numpy as np

 
class MinimalPublisherAndSubscriber(Node):

    def __init__(self):
        super().__init__('publisher_joint_controller')
        self.publisher_ = self.create_publisher(JointTrajectory, '/joint_trajectory_controller/joint_trajectory', 10) #il tipo di messaggio e' il terzo campo. Il nome del topic lo vedi da ros2 topic list       
        timer_period = 0.01  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        self.subscription_joint_states = self.create_subscription(
            JointState, #qui è un tipo 
            '/joint_states',
            self.listener_callback_joints,
            10)
        self.subscription_joint_states #to prevent unused warning

        self.joints_postion = np.zeros(3)
        self.joints_velocities = np.zeros(12)

    #Quando ti iscrivi a un topic, basta prendere i dati e salvarli dove vuoi. il problema è pubblicare, perché devi riempire ogni campo del messaggio del tipo giusto
    def listener_callback_joints(self, joints_data): #joints data is an alias of sensor_msgs.msg.JointState. Therefore I can access to each field of the struct just using data
        self.joints_postion = joints_data.position
        self.joints_velocities = joints_data.velocity

        #print("positions RKFE: ", self.joints_postion[2])

    
    def timer_callback(self):
        msg = JointTrajectory() #terzo campo di trajectory_msgs.msg. Chiami la classe e il messaggio avra' la sua struttura
        #inizialmente il suo campo points sarà vuoto. Dovrai fare un append per metterci qualcosa
        msg.joint_names = ["giunto_1", "giunto_2", "giunto_3"]
 
        point = JointTrajectoryPoint() #include, position[], vel[], acc[], time_from_start[] fields of the JointTrajectory)() class points
        point.positions = [0.1, 0.2, 0.4]

        time_from_start = Duration()
        time_from_start.sec = 2
        point.time_from_start = time_from_start

        msg.points.append(point)
        
        self.publisher_.publish(msg)
        self.get_logger().info('Publishing on joints: "%s"' % msg.joint_names)
        #self.get_logger().info('command: "%s"' % msg.points)
         


def main(args=None):
    rclpy.init(args=args)

    minimal_publisher = MinimalPublisherAndSubscriber()

    rclpy.spin(minimal_publisher) #to activate the callback

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
 