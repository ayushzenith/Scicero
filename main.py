import datetime
from itertools import count
from shutil import move
from tkinter.ttk import LabeledScale
import mediapipe as mp
import datetime
import cv2
import numpy as np
import keyboard
from interbotix_xs_modules.arm import InterbotixManipulatorXS

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

calibrate = True
prevCoords = []
calibratedCoords = []
rt1Button = 0
rt2Button = 0
aButton = 0

lt1Button = 0
lt2Button = 0
openGrip = 0

numPlayers = 1
arrows = []
overlayTextPositionArr = []
# Loads robot arm, needs a plugged in px150 arm activated in another terminal window
bot = InterbotixManipulatorXS("px150", "arm", "gripper")

class Controller:
	def __init__(self):
		self.left_trigger = 0
		self.left_bumper = 0
		self.right_trigger = 0
		self.right_bumper = 0
		self.overlayText = 0
		self.Abutton = 0
		self.player = 0
	def __add__(self, other):
		ret = Controller()
		ret.left_trigger = self.left_trigger + other.left_trigger
		ret.left_bumper = self.left_bumper + other.left_bumper
		ret.right_trigger = self.right_trigger + other.right_trigger
		ret.right_bumper = self.right_bumper + other.right_bumper
		ret.overlayText = self.overlayText + other.overlayText
		ret.Abutton = self.Abutton + other.Abutton
		return ret
	def __truediv__(self, other):
		ret = Controller()
		ret.left_trigger = self.left_trigger / other
		ret.left_bumper = self.left_bumper / other
		ret.right_trigger = self.right_trigger / other
		ret.right_bumper = self.right_bumper / other
		ret.overlayText = self.overlayText / other
		ret.Abutton = self.Abutton / other
		return ret
	def __str__(self):
		ret = ""
		ret += "Left Trigger: " + str(self.left_trigger) + "\n"
		ret += "Left Bumper: " + str(self.left_bumper) + "\n"
		ret += "Right Trigger: " + str(self.right_trigger) + "\n"
		ret += "Right Bumper: " + str(self.right_bumper) + "\n"
		ret += "overlayText: " + str(self.overlayText) + "\n"
		ret += "A Button: " + str(self.Abutton) + "\n"
		return ret


def getDelta(newCoords, oldCoords):
	deltaArray = [] # array of delta coords
	deltaAverageX = 0
	deltaAverageY = 0
	deltaAverageZ = 0
	deltaAverage = 0

	if (oldCoords == [] or newCoords == [] or oldCoords == None or newCoords == None): # base case if we dont have previous hand coords
		deltaArray.append(100)
		return 2
	else: # Regular case where we take new coords and subtract from prev coords
		for i in range(len(newCoords)):
			for j in range(len(newCoords[i].landmark)):
				print("--------------------")
				deltax = abs(newCoords[i].landmark[j].x - oldCoords[i].landmark[j].x)
				deltay = abs(newCoords[i].landmark[j].y - oldCoords[i].landmark[j].y)
				deltaz = abs(newCoords[i].landmark[j].z - oldCoords[i].landmark[j].z)
				deltaArray.append({"deltax": deltax, "deltay": deltay, "deltaz": deltaz})

	for i in deltaArray:
		print(i)
		deltaAverageX += i["deltax"]
		deltaAverageY += i["deltay"]
		deltaAverageZ += i["deltaz"]

	deltaAverageX /= float(len(deltaArray))
	deltaAverageY /= float(len(deltaArray))
	deltaAverageZ /= float(len(deltaArray))

	deltaAverage = (deltaAverageX + deltaAverageY + deltaAverageZ) / 3.0

	#print(deltaAverage)
	return deltaAverage

def checkButtonPress(movementDiff, calibratedMovementDiff, movementRatio):
	if (movementDiff < calibratedMovementDiff * movementRatio):
		return 1
	else:
		return 0


def xDiff(curCoords, nailNumber, nuckleNumber, handNum):
	if (curCoords and curCoords[handNum]):
		nuckleDiff = abs(curCoords[handNum].landmark[17].y - curCoords[handNum].landmark[5].y)
		calibratednuckleDiff =  abs(calibratedCoords[handNum].landmark[17].y - calibratedCoords[handNum].landmark[5].y)
		movementDiff = abs(curCoords[handNum].landmark[nailNumber].x - curCoords[handNum].landmark[nuckleNumber].x)
		calibratedMovementDiff = abs(calibratedCoords[handNum].landmark[nailNumber].x - calibratedCoords[handNum].landmark[nuckleNumber].x) * nuckleDiff/calibratednuckleDiff
		return (movementDiff, calibratedMovementDiff)
	return (0,0)

def yDiff(curCoords, nailNumber, nuckleNumber, handNum):
	if (curCoords and curCoords[handNum]):
		nuckleDiff = abs(curCoords[handNum].landmark[17].y - curCoords[handNum].landmark[5].y)
		calibratednuckleDiff =  abs(calibratedCoords[handNum].landmark[17].y - calibratedCoords[handNum].landmark[5].y)
		movementDiff = abs(curCoords[handNum].landmark[nailNumber].y - curCoords[handNum].landmark[nuckleNumber].y)
		calibratedMovementDiff = abs(calibratedCoords[handNum].landmark[nailNumber].y - calibratedCoords[handNum].landmark[nuckleNumber].y) * nuckleDiff/calibratednuckleDiff
		return (movementDiff, calibratedMovementDiff)
	return (0,0)

def triggerPosition(movementDiff, calibratedMovementDiff):
	if(not movementDiff):
		return 0
	ratio = movementDiff/calibratedMovementDiff
	ratio -= 1
	ratio /= 0.75 # scaling param that has yet to be determined
	ratio = max(ratio, -1) # bound the overlayText between -1 and 1
	ratio = min(ratio, 1)
	return ratio


controllers = []
temp_controllers = []
for i in range(numPlayers):
	controllers.append(Controller())
	temp_controllers.append([Controller(), Controller(), Controller()])
# For webcam input:
cap = cv2.VideoCapture(0)
startTime = datetime.datetime.now()
counter = 0
img_height, img_width = 100, 150
n_channels = 3
joycon = np.zeros((img_height, img_width, n_channels), dtype=np.uint8)

# Try-except block is for exiting gracefully - when no hands are detected on screen, the program will exit the detection loop
# and reset the robot to home position before ending the program
try:
	with mp_hands.Hands(
		model_complexity=1,
		max_num_hands=2,
		min_detection_confidence=0.5,
		min_tracking_confidence=0.7) as hands:

		# These numbers are used to check hand position differences every 30 frames - if every frame was checked it would be difficult
		# to move enough in one frame to input a change
		lastIndexPos = None
		frameCounter = 0
		frames = 30

		# Extend arm
		bot.arm.go_to_home_pose()

		while cap.isOpened():
			success, image = cap.read()
			if not success:
				print("Ignoring empty camera frame.")
				# If loading a video, use 'break' instead of 'continue'.
				continue

			frameCounter += 1
			
			counter += 1
			leftConroller = 0
			rightConroller = 0

			# These hyperparameters are used to prevent the arm from extending too far in one direction, which might cause it's muscles to fail
			distanceCap = 0.75
			currentExtension = 0

			# To improve performance, optionally mark the image as not writeable to
			# pass by reference.
			image.flags.writeable = False
			image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
			results = hands.process(image)
			

			# results.multi_hand_landmark stores each hand landmark x,y,z
			# do calibration

			curTime = datetime.datetime.now()
			if ((curTime - startTime).total_seconds() < 5):
				image = cv2.flip(image, 1)
				cv2.putText(image, "CALIBRATING", (int(image.shape[0]//2), int(image.shape[1]//10)),
						cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 5)
				image = cv2.flip(image, 1)
			if (4 < (curTime - startTime).total_seconds() < 5):
				calibratedCoords = results.multi_hand_landmarks
				print("calibration complete")
			if (calibratedCoords != None and len(calibratedCoords) > 0):

				# If no previous position has been recorded for the left hand(the program just started running), record the initial positoin
				if (lastIndexPos is None):
					lastIndexPos = results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
				elif (frameCounter >= frames):
					frameCounter = 0;
					new = results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
					# If the x position of the left hand is a great enough difference from the last recorded position, move the arm left or right
					if (abs(new.x - lastIndexPos.x) > 0.05):
						#print("Change in x:" + str((new.x - lastIndexPos.x)/10))
						#bot.arm.set_ee_cartesian_trajectory(x= (new.x - lastIndexPos.x)/10)
						# This will move the waist to the position of the new x, scaled to the 180 rotation of the arm
						bot.arm.set_single_joint_position("waist", np.pi / 2 - np.pi * (1 - new.x))
						lastIndexPos.x = new.x
					# If the y position of the left hand is a great enough change, move the arm forward or backward
					if (abs(new.y - lastIndexPos.y) > 0.05):
						# if this movement would take the arm over the extension cap, the change is capped at reaching that cap
						dx = 0.3 * (0.5 - new.y)
						if (dx + currentExtension > distanceCap): dx = distanceCap - currentExtension
						if (dx + currentExtension < -distanceCap): dx = -distanceCap - currentExtension
						# this will move the arm an amount equal to how far up or down from the center the detected hand is
						bot.arm.set_ee_cartesian_trajectory(x=(dx))
						currentExtension += dx
						lastIndexPos.y = new.y


				if results.multi_handedness != None:
					for i in range(len(results.multi_handedness)):
						if (results.multi_handedness[i].classification[0].label == "Left"):
							if(leftConroller >= numPlayers):
								image = cv2.flip(image, 1)
								cv2.putText(image, "Please move your hands into view", (int(image.shape[0]//2), int(image.shape[1]//10)),
									cv2.FONT_HERSHEY_SIMPLEX, 3, (255,0,0), 5)
								image = cv2.flip(image, 1)
								continue
							try:
								(rt1Movementdiff, rt1CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 8, 5, i)
								(rt2Movementdiff, rt2CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 12, 9, i)
								(aMovementdiff, aCalibratedMovementDiff) = yDiff(results.multi_hand_landmarks, 4, 5, i)
							except IndexError:
								image = cv2.flip(image, 1)
								cv2.putText(image, "Please move your hands into view", (int(image.shape[0]//2), int(image.shape[1]//10)),
									cv2.FONT_HERSHEY_SIMPLEX, 3, (255,0,0), 5)
								image = cv2.flip(image, 1)
								continue


							rt1ButtonPressed = checkButtonPress(rt1Movementdiff, rt1CalibratedMovementDiff, 0.85)
							rt2ButtonPressed = checkButtonPress(rt2Movementdiff, rt2CalibratedMovementDiff, 0.87)
							aButtonPressed = checkButtonPress(aMovementdiff, aCalibratedMovementDiff, 0.90)

							print(leftConroller)
							temp_controllers[leftConroller][counter%3].right_trigger = rt1ButtonPressed
							temp_controllers[leftConroller][counter%3].right_bumper = rt2ButtonPressed
							temp_controllers[leftConroller][counter%3].Abutton = aButtonPressed
							if (counter%3 == 0):
								controllers[leftConroller] = (temp_controllers[leftConroller][0] + temp_controllers[leftConroller][1] + temp_controllers[leftConroller][2])/3

							if (rt1ButtonPressed == 1):
								rt1Button +=1
								if(rt1Button < 2):
									print("Right index Pressed")
									#bot.gripper.open()
									arrows.append([(130, 13), (110, 13), (0, 0, 255), 4, 0.5])
							else:
								rt1Button = 0

							if (rt2ButtonPressed == 1):
								rt2Button += 1
								if(rt2Button < 2):
									print("Right middle Pressed")
									#bot.arm.go_to_home_pose()
									arrows.append([(130, 25), (110, 25), (0, 0, 255), 4, 0.5])
							else:
								rt2Button = 0

							if (aButtonPressed == 1):
								aButton += 1
								# If right thumb is pressed, invert whether the arm is gripping
								if(aButton < 2):
									print("Right thumb Pressed")
									if openGrip == 1:
										bot.gripper.close()
										openGrip = 0
									else:
										bot.gripper.open()
										openGrip = 1
									#bot.arm.set_single_joint_position("waist", 0)
									#bot.arm.go_to_sleep_pose()
									arrows.append([(130, 65), (110, 65), (0, 0, 255), 4, 0.5])
							else:
								aButton = 0
							leftConroller+=1
						elif (results.multi_handedness[i].classification[0].label == "Right"):
							if(rightConroller >= numPlayers):
								image = cv2.flip(image, 1)
								cv2.putText(image, "Please move your hands into view", (int(image.shape[0]//2), int(image.shape[1]//10)),
									cv2.FONT_HERSHEY_SIMPLEX, 3, (255,0,0), 5)
								image = cv2.flip(image, 1)
								continue
							try:
								(lt1Movementdiff, lt1CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 8, 5, i)
								(lt2Movementdiff, lt2CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 12, 9, i)
								m, c = xDiff(results.multi_hand_landmarks, 4, 5, i)
								m_y, c_y = yDiff(results.multi_hand_landmarks, 4, 2, i)
							except:
								image = cv2.flip(image, 1)
								cv2.putText(image, "Please move your hands into view", (int(image.shape[0]//2), int(image.shape[1]//10)),
									cv2.FONT_HERSHEY_SIMPLEX, 3, (255,0,0), 5)
								image = cv2.flip(image, 1)
								continue

							lt1ButtonPressed = checkButtonPress(lt1Movementdiff, lt1CalibratedMovementDiff, 0.90)
							lt2ButtonPressed = checkButtonPress(lt2Movementdiff, lt2CalibratedMovementDiff, 0.90)

							overlayTextPosition = triggerPosition(m,c)
							overlayTextPositionY = triggerPosition(m_y,c_y)

							overlayTextPositionArr.append(overlayTextPosition)
							overlayTextPositionArr.append(overlayTextPositionY)

							temp_controllers[rightConroller][counter%3].left_trigger = lt1ButtonPressed
							temp_controllers[rightConroller][counter%3].left_bumper = lt2ButtonPressed
							temp_controllers[rightConroller][counter%3].overlayText = overlayTextPosition
							if (counter%3 == 0):
								controllers[rightConroller] = (temp_controllers[rightConroller][0] + temp_controllers[rightConroller][1] + temp_controllers[rightConroller][2])/3

							if (lt1ButtonPressed == 1):
								lt1Button += 1
								if(lt1Button < 2):
									print("Left index Pressed")
									#bot.gripper.close()
									arrows.append([(55, 13), (35, 13), (0, 0, 255), 4, 0.5])
							else:
								lt1Button = 0

							if (lt2ButtonPressed == 1):
								lt2Button += 1
								if(lt2Button < 2):
									print("Left middle Pressed")
									#bot.gripper.close()
									arrows.append([(55, 25), (35, 25), (0, 0, 255), 4, 0.5])
							else:
								lt2Button = 0
							rightConroller+=1
			# Draw the hand annotations on the image.
			image.flags.writeable = True
			image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
			if results.multi_hand_landmarks:
				for hand_landmarks in results.multi_hand_landmarks:
					mp_drawing.draw_landmarks(
						image,
						hand_landmarks,
						mp_hands.HAND_CONNECTIONS,
						mp_drawing_styles.get_default_hand_landmarks_style(),
						mp_drawing_styles.get_default_hand_connections_style())
			# Flip the image horizontally for a selfie-view display.
			image = cv2.flip(image, 1)
			image[0:joycon.shape[0], 0:joycon.shape[1]] = joycon

			#for i in arrows:
			#	image = cv2.arrowedLine(image, i[0], i[1], i[2], i[3], tipLength = i[4])

			#for i in overlayTextPositionArr:
			#	image = cv2.putText(image, str(round(i, 5)), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

			if (len(overlayTextPositionArr) > 0):
				image = cv2.putText(image, "x:" + str(round(overlayTextPositionArr[0], 5)), (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0),2)
				image = cv2.putText(image, "y: " + str(round(overlayTextPositionArr[1], 5)), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0),2)
			overlayTextPositionArr = []
			arrows = []
			cv2.imshow('MediaPipe Hands', image)
			if cv2.waitKey(5) & 0xFF == 27:
				break
	cap.release()
except:
	cap.release()
	bot.arm.set_single_joint_position("waist", 0)
	bot.arm.go_to_sleep_pose()
	bot.gripper.open()
