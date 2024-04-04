import os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
os.sys.path.insert(0, parentdir)

import pybullet as pb
import math
import pybullet_data
import time

class jaco:

    def __init__(self, timeStep, urdfRootPath=pybullet_data.getDataPath(), renders=False):
        self.urdfRootPath = urdfRootPath
        self._timeStep = timeStep
        self.renders = renders
        self.maxVelocity = .35
        self.maxForce = 200.
        self.fingerThumbForce = 3
        self.fingerAForce = 3
        self.fingerBForce = 3
        self.fingerforce = 6
        self.fingertipforce = 2 
        self.fingerIndices = [9, 11, 13]
        self.fingerThumbtipforce = 3 * self.fingertipforce
        self.fingerTipForce = 2
        self.fingertipIndices = [10, 12, 14]
        self.useInverseKinematics = 1
        self.useSimulation = 1
        self.useNullSpace = 42  # = 14+14+14 ll ul rp
        self.useOrientation = 1
        self.jacoEndEffectorIndex = 8 # use to get pose of end effector
        #self.jacoGripperIndex:
        self.jacoThumbIndex = 9
        self.jacoFingerAIndex = 11 
        self.jacoFingerBIndex = 13
        # Lower limits for null space
        self.ll = [0,0,-6.28318530718,0.820304748437,0.331612557879,-6.28318530718,-6.28318530718,-6.28318530718,0,0,0,0,0,0,0]
        # Upper limits for null space
        self.ul = [0,0,6.28318530718,5.46288055874,5.9515727493,6.28318530718,6.28318530718,6.28318530718,0,2,2,2,2,2,2]
        # Joint ranges for null space
        self.jr = [5.8, 4, 5.8, 4, 5.8, 4, 6]
        # Restposes for null space
        self.rp = [0,0.25,1.85,3,1.25,3.5,4.5,3,3,0.5,0,0.5,0,0.5,0]
        # Joint damping coefficents
        self.jd = [
            0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001,
            0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001,
            0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001
        ]
        self.reset()

    def reset(self):
        
        objects = pb.loadURDF(os.path.join('jaco/j2n6s300_color copy.urdf',), useFixedBase=True)
        # Convert into to tuple
        objects = (objects,)
        #print(type(objects))
        self.jacoUid = objects[0]

        # Keep robot at same position after every reset
        jaco_orientation_euler = [0, 0, 0]
        jaco_orientation_quaternion = pb.getQuaternionFromEuler(jaco_orientation_euler)
        # pb.resetBasePositionAndOrientation(self.jacoUid, [-0.76, -0.06, 0.47],jaco_orientation_quaternion)
        pb.resetBasePositionAndOrientation(self.jacoUid, [-0.5, -0.05, -0.28], jaco_orientation_quaternion)


        self.jointPositions = [# finger indices = [9 - 14]
            0, 0, 0, 2.7, 5.7, -0.6, 1.60, 2.8, 0, 0, 0.25, 0, 0.25, 0, 0.25
        ]
        self.numJoints = pb.getNumJoints(self.jacoUid)
        
        for jointIndex in range(self.numJoints):
            pb.resetJointState(self.jacoUid, jointIndex, self.jointPositions[jointIndex])
            pb.setJointMotorControl2(self.jacoUid,
                              jointIndex,
                              pb.POSITION_CONTROL,
                              targetPosition=self.jointPositions[jointIndex],
                              force=self.maxForce) 
    
        # Change dynamics of gripper and finger to grasp objects
        # TODO: Change dynamics directly in urdf file of jaco arm
        for i in range(9,14):
            pb.changeDynamics(self.jacoUid,i,mass=0.3,lateralFriction=1,restitution=0,spinningFriction=0.1,contactStiffness=30000,contactDamping=1000)

        pb.changeDynamics(self.jacoUid,8,mass=0.5,lateralFriction=1,restitution=0.0,spinningFriction=0.1,contactStiffness=10,contactDamping=10)
        self.endEffectorPos = [0, 0, 0.035]

        self.motorNames = []
        self.motorIndices = []

        for i in range(self.numJoints):
            jointInfo = pb.getJointInfo(self.jacoUid, i)
            qIndex = jointInfo[3]
            if qIndex > -1:
                #print("motorname")
                #print(jointInfo[1])
                self.motorNames.append(str(jointInfo[1]))
                self.motorIndices.append(i)

    
    def apply_move(self, motorCommands):

        if (self.useInverseKinematics):

            dx = motorCommands[0]
            dy = motorCommands[1]
            dz = motorCommands[2]

            state = pb.getLinkState(self.jacoUid, self.jacoEndEffectorIndex)
            endEffectorPos = list(state[0])

            # Option 1, better in simulation
            endEffectorPos[0] = endEffectorPos[0] + dx
            endEffectorPos[1] = endEffectorPos[1] + dy
            endEffectorPos[2] = endEffectorPos[2] + dz
            if endEffectorPos[2] < 0.01:
                endEffectorPos[2] = 0.01
            pos = endEffectorPos   
        
            # Option 2, this better for real experiment
            # self.endEffectorPos[0] = self.endEffectorPos[0] + dx
            # self.endEffectorPos[1] = self.endEffectorPos[1] + dy
            # self.endEffectorPos[2] = self.endEffectorPos[2] + dz
            # pos = self.endEffectorPos
            
            # Leave wirst orientation like it is for now   
            orn = state[1] 
                
            if (self.useNullSpace == 1):
                if (self.useOrientation == 1):
                    jointPoses = pb.calculateInverseKinematics(self.jacoUid, self.jacoEndEffectorIndex, pos,
                                                                orn, self.ll, self.ul, self.jr, self.rp)
                else:
                    jointPoses = pb.calculateInverseKinematics(self.jacoUid,
                                                                self.jacoEndEffectorIndex,
                                                                pos,
                                                                lowerLimits=self.ll,
                                                                upperLimits=self.ul,
                                                                jointRanges=self.jr,
                                                                restPoses=self.rp)
            else:
                if (self.useOrientation == 1):
                    # This is selected for computation
                    jointPoses = pb.calculateInverseKinematics(self.jacoUid,
                                                                self.jacoEndEffectorIndex,
                                                                pos, # state[0],#pos,
                                                                orn, #state[1], #orn,
                                                                jointDamping=self.jd)
                else:
                    jointPoses = pb.calculateInverseKinematics(self.jacoUid, self.jacoEndEffectorIndex, pos)

            # Insert zeros for the non-movable joints, because pb.calculateInverseKinematics returns just a tuple for the movable joints    
            list_jointPoses = list(jointPoses)
            list_jointPoses.insert(0, 0)
            list_jointPoses.insert(1, 0)
            list_jointPoses.insert(8, 0)

            jointPoses = tuple(list_jointPoses)

            # Apply new joint poses to the robotic arm 
            if (self.useSimulation):
                pb.setJointMotorControlArray(
                            bodyUniqueId=self.jacoUid,
                            jointIndices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                            controlMode=pb.POSITION_CONTROL,
                            targetPositions=jointPoses,   
                            targetVelocities=[0]*len(jointPoses),
                            forces=[self.maxForce]*len(jointPoses),
                            velocityGains=[1]*len(jointPoses)
                        )
                pb.stepSimulation()
            else:
                # Reset the joint state (ignoring all dynamics, not recommended to use during simulation)
                for i in range(self.numJoints):
                    pb.resetJointState(self.jacoUid, i, jointPoses[i])

        else:
            for action in range(len(motorCommands)):
                motor = self.motorIndices[action]
                pb.setJointMotorControl2(self.jacoUid,
                                        motor,
                                        pb.POSITION_CONTROL,
                                        targetPosition=motorCommands[action],
                                        force=self.maxForce)
    


    def apply_grasp(self, initial_finger_angle=0.6, final_finger_angle=5, step_increment=0.001, finger_force_multiplier=3,  AutoLift=True):
        # Close fingers
        
        finger_angle = initial_finger_angle
        
        for _ in range (200):
            pb.setJointMotorControlArray(
                bodyUniqueId=self.jacoUid,
                jointIndices=self.fingerIndices,
                controlMode=pb.POSITION_CONTROL,
                targetPositions=[finger_angle] * len(self.fingerIndices),
                targetVelocities=[0] * len(self.fingerIndices),
                forces=[self.fingerThumbForce * finger_force_multiplier,
                        self.fingerAForce * finger_force_multiplier,
                        self.fingerBForce * finger_force_multiplier],
                velocityGains=[1] * len(self.fingerIndices)
            )
            pb.stepSimulation()
            if self.renders:
                time.sleep(self._timeStep)
            finger_angle += step_increment

            if finger_angle > final_finger_angle:
                finger_angle = final_finger_angle # Upper limit
                # break

        # Close fingertips
        tip_angle = initial_finger_angle  # Re-use initial_finger_angle if starting from the same position
        for _ in range(200):

            pb.setJointMotorControlArray(
                bodyUniqueId=self.jacoUid,
                jointIndices=self.fingertipIndices,
                controlMode=pb.POSITION_CONTROL,
                targetPositions=[tip_angle] * len(self.fingertipIndices),
                targetVelocities=[0] * len(self.fingertipIndices),
                forces=[self.fingerThumbtipforce * finger_force_multiplier,
                        self.fingertipforce * finger_force_multiplier,
                        self.fingertipforce * finger_force_multiplier],
                velocityGains=[1] * len(self.fingertipIndices)
            )
            pb.stepSimulation()
            tip_angle += step_increment
            
            if tip_angle > final_finger_angle:
                tip_angle = final_finger_angle # Upper limit

        # # Lift gripper after grasp  
        if AutoLift:  
            for _ in range(90): # 160
                self.apply_move([0, 0, 0.01])
                pb.stepSimulation()
                if self.renders:
                    time.sleep(self._timeStep)


    def apply_release(self, initial_finger_angle=0.6, final_finger_angle=0, step_increment=0.001, finger_force_multiplier=1, AutoLower=True):
        # Open fingers

        # Lower gripper after release
        if AutoLower:
            for _ in range(45):
                self.apply_move([0, 0, -0.01])  # Assuming apply_move function exists for moving the arm
                pb.stepSimulation()
                if self.renders:
                    time.sleep(self._timeStep)

        # Open fingers
        finger_angle = initial_finger_angle
        for _ in range(700):
            pb.setJointMotorControlArray(
                bodyUniqueId=self.jacoUid,
                jointIndices=self.fingerIndices,
                controlMode=pb.POSITION_CONTROL,
                targetPositions=[finger_angle] * len(self.fingerIndices),
                targetVelocities=[0] * len(self.fingerIndices),
                forces=[self.fingerThumbForce * finger_force_multiplier,
                        self.fingerAForce * finger_force_multiplier,
                        self.fingerBForce * finger_force_multiplier],
                velocityGains=[1] * len(self.fingerIndices)
            )
            pb.stepSimulation()
            finger_angle -= step_increment
            
            if finger_angle < final_finger_angle:
                finger_angle = final_finger_angle # Lower limit

            # if self.renders:
            #     time.sleep(self._timeStep)

        # Open fingertips
        tip_angle = initial_finger_angle
        for _ in range(500):
            pb.setJointMotorControlArray(
                bodyUniqueId=self.jacoUid,
                jointIndices=self.fingertipIndices,
                controlMode=pb.POSITION_CONTROL,
                targetPositions=[tip_angle] * len(self.fingertipIndices),
                targetVelocities=[0] * len(self.fingertipIndices),
                forces=[self.fingerThumbtipforce * finger_force_multiplier,
                        self.fingertipforce * finger_force_multiplier,
                        self.fingertipforce * finger_force_multiplier],
                velocityGains=[1] * len(self.fingertipIndices)
            )
            pb.stepSimulation()
            tip_angle -= step_increment
            
            if tip_angle < final_finger_angle:
                tip_angle = final_finger_angle # Lower limit

            # if self.renders:
            #     time.sleep(self._timeStep)








    