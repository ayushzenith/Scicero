# Scicero

After robot arm is running(must be px150 or this will need to be changed in main.py), the webcam will launch. In order to calibrate, hold both hands up before the camera and ensure your right thumb is extended - this is so the algorithm will detect when the right thumb is pressed down.

After calibration, the robot arm can be controlled as follows:
moving your left index finger to the left or right will rotate the arm to match your approximate position on the camera with it's waist
moving your left index above or below the center of the camera will input a move command forward or back, with magnitute equal to the distance from the center - this is not relative to old position like left/right movement
moving both left/right and up/down will issue both commands simultaneously

the right thumb may additionally be pressed as if one were pressing a button to open/close the gripper of the arm
