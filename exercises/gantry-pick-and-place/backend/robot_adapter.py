from robot_sim import Robot, GripperState

MOTION_EPSILON = 1e-6
TARGET_TOLERANCE = 1e-3

class RobotAdapter:
    def __init__(self, robot: Robot):
        self._robot = robot

    def set_home_position(self, home_pos: tuple[float, float, float]) -> None:
        self._robot.home_position = list(home_pos)

    def get_position(self) -> tuple[float, float, float]:
        pos = self._robot.current_position
        return (pos[0], pos[1], pos[2])

    def get_velocity(self) -> tuple[float, float, float]:
        vel = self._robot.axis_speed
        return (vel[0], vel[1], vel[2])

    def is_moving(self) -> bool:
        return any(abs(v) > MOTION_EPSILON for v in self._robot.axis_speed)

    def stop_motion(self) -> None:
        self._robot.axis_speed = [0, 0, 0]

    def is_gripper_closed(self) -> bool:
        return self._robot.gripper_state == GripperState.CLOSED

    def _is_at_target(self, target: tuple[float, float, float]) -> bool:
        current = self._robot.current_position
        return all(abs(c - t) <= TARGET_TOLERANCE for c, t in zip(current, target))

    def move_to(self, target: tuple[float, float, float], speed: float) -> bool:
        _, axis_speed, error = self._robot.move_to(list(target), speed=int(speed))
        if error:
            raise RuntimeError(f"Simulator movement error: {error}")
        
        stopped = all(abs(v) <= MOTION_EPSILON for v in axis_speed)
        at_target = self._is_at_target(target)
        return stopped and at_target

    def move_home(self, speed: float) -> bool:
        _, axis_speed, error = self._robot.move_home(speed=int(speed))
        if error:
            raise RuntimeError(f"Simulator homing error: {error}")
        
        stopped = all(abs(v) <= MOTION_EPSILON for v in axis_speed)
        at_target = self._is_at_target(tuple(self._robot.home_position))
        return stopped and at_target

    def close_gripper(self) -> None:
        if self._robot.gripper_state != GripperState.CLOSED:
            self._robot.closed_gripper()

    def open_gripper(self) -> None:
        if self._robot.gripper_state != GripperState.OPEN:
            self._robot.open_gripper()
