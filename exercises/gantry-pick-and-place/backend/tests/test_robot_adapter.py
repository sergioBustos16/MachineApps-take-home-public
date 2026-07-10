import pytest
from robot_sim import Robot, GripperState
from robot_adapter import RobotAdapter

def test_robot_adapter_initialization():
    robot = Robot(initial_position=[10.0, 20.0, 30.0])
    adapter = RobotAdapter(robot)
    
    assert adapter.get_position() == (10.0, 20.0, 30.0)
    assert adapter.get_velocity() == (0.0, 0.0, 0.0)
    assert not adapter.is_moving()
    assert not adapter.is_gripper_closed()

def test_robot_adapter_gripper():
    robot = Robot()
    adapter = RobotAdapter(robot)
    
    assert not adapter.is_gripper_closed()
    adapter.close_gripper()
    assert adapter.is_gripper_closed()
    assert robot.gripper_state == GripperState.CLOSED
    
    adapter.open_gripper()
    assert not adapter.is_gripper_closed()
    assert robot.gripper_state == GripperState.OPEN

def test_robot_adapter_movement_direct():
    robot = Robot(initial_position=[0.0, 0.0, 0.0])
    adapter = RobotAdapter(robot)
    
    # Check simple move_to target
    # Since move_to runs over multiple increments, the first call plans the motion and starts moving
    completed = adapter.move_to((100.0, 0.0, 0.0), speed=50.0)
    assert not completed  # Not finished instantly on first tick
    assert adapter.is_moving()
    assert adapter.get_velocity()[0] > 0.0
