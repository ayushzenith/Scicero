from interbotix_xs_modules.arm import InterbotixManipulatorXS
import numpy as np

def main():
    bot = InterbotixManipulatorXS("px150", "arm", "gripper")
    bot.arm.go_to_home_pose()
    #bot.arm.set_ee_cartesian_trajectory(x=0.1,z=0.23)
    #bot.arm.set_ee_cartesian_trajectory(z=-0.2)
    #bot.arm.set_ee_cartesian_trajectory(x=-0.2)
    #bot.arm.set_ee_cartesia(new.x - lastIndexPos.x) / 10n_trajectory(z=0.2)
    #bot.arm.set_ee_cartesian_trajectory(x=0.2)
    #bot.arm.set_single_joint_position("waist", np.pi/2.0)
    bot.arm.set_single_joint_position("waist", 0)
    bot.arm.go_to_sleep_pose()
    bot.gripper.open()

if __name__=='__main__':
    main()
 