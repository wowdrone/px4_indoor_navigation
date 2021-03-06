#!/usr/bin/env python
import PID
import rospy
from geometry_msgs.msg import Point, PoseStamped
from mavros_msgs.msg import *

class Controller:
	""" Implements an altitude PID controller using velocity commands.
	Allows to send altitude setpoints and velocity setpoints in XY plane
	"""
	def __init__(self):

		# flight mode
		self.state = " "
		# Arm state
		self.IS_ARMED = False

		self.LANDED_STATE = 1 # on ground
		# instantiate setpoint msg
		self.sp = PositionTarget()
		# set mask to accept velocity setpoints and yaw angle
		self.sp.type_mask    = int('010111000111', 2)
		# set frame type, LOCAL_NED
		self.sp.coordinate_frame= 1

		# flying altitude
		self.ALT_SP = rospy.get_param("alt_sp", 1.0)
		# maximum velocity setpoints
		self.MAX_VUP = rospy.get_param("MAX_VUP", 2.0)
		self.MAX_VDOWN = rospy.get_param("MAX_VDOWN", 0.5)

		self.vxsp = 0.
		self.vysp = 0.
		# initialize setpoint
		self.sp.velocity.x = 0.
		self.sp.velocity.y = 0.
		self.sp.velocity.z = 0.
		self.sp.yaw = 0.
		
		# message for current position of the drone
		self.local_pos = Point(0.0, 0.0, 0.0)

		# PID controller for altitude
		self.Kp = rospy.get_param("alt_Kp", 1.0)
		self.Ki = rospy.get_param("alt_Ki", 0.1)
		self.Kd = rospy.get_param("alt_Kd", 0.01)
		self.Ts = rospy.get_param("Ts", 0.1) # default 10Hz

		self.pid = PID.PID(self.Kp, self.Ki, self.Kd)
		self.pid.setSampleTime(self.Ts)

	def posCb(self, msg):
		self.local_pos.x = msg.pose.position.x
		self.local_pos.y = msg.pose.position.y
		self.local_pos.z = msg.pose.position.z

	def spCb(self, msg):
		self.vxsp = msg.x
		self.vysp = msg.y
		self.ALT_SP = msg.z

	def stateCb(self, msg):
		self.state = msg.mode
		self.IS_ARMED = msg.armed

	def landingStateCb(self, msg):
		self.LANDED_STATE = msg.landed_state

	def gainsCb(self, msg):
		self.pid.setKp(msg.x)
		self.pid.setKi(msg.y)
		self.pid.setKd(msg.z)

	def update(self):
		error = self.ALT_SP - self.local_pos.z

		self.pid.SetPoint = self.ALT_SP
		if self.IS_ARMED and self.LANDED_STATE > 1 and slef.state == "OFFBOARD":
			self.pid.I_TERM_IS_ACTIVE = True
		else:
			self.pid.I_TERM_IS_ACTIVE = False

		self.pid.update(self.local_pos.z)
		self.sp.velocity.z = self.pid.output
		if self.sp.velocity.z > self.MAX_VUP:
			self.sp.velocity.z = self.MAX_VUP
                if self.sp.velocity.z < -1.0*self.MAX_VDOWN:
                        self.sp.velocity.z = -1.0*self.MAX_VDOWN

		self.sp.velocity.x = self.vxsp
		self.sp.velocity.y = self.vysp

def main():
	# intiate node
	rospy.init_node("altitude_vxy_controller", anonymous=True)

	# instantiate controller
	cnt = Controller()

	# ROS loop rate, [Hz]
	rate = rospy.Rate(20.0)

	# subscribtions
	rospy.Subscriber("mavros/local_position/pose", PoseStamped, cnt.posCb)
	rospy.Subscriber("~alt_vxy_sp",  Point, cnt.spCb)
	rospy.Subscriber("mavros/state", State, cnt.stateCb)
	rospy.Subscriber("mavros/extedned_state", ExtendedState, cnt.landingStateCb)
	rospy.Subscriber("~change_gains", Point, cnt.gainsCb)

	# Setpoint publisher    
	sp_pub = rospy.Publisher('mavros/setpoint_raw/local', PositionTarget, queue_size=1)

	while not rospy.is_shutdown():
		cnt.update()
		sp_pub.publish(cnt.sp)
		rate.sleep()

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass

