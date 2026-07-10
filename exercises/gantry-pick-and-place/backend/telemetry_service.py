from typing import Optional
from domain.models import TelemetrySnapshot, Vector3, WorkspaceBounds, AxisBounds
from domain.enums import RobotStatus
from gantry_fsm import GantryRobotStateMachine, RobotOperationStates, PickAndPlaceStates

STATIC_LIMITS = WorkspaceBounds(
    x=AxisBounds(min=-1000.0, max=1000.0),
    y=AxisBounds(min=-1000.0, max=1000.0),
    z=AxisBounds(min=-1000.0, max=1000.0)
)

def derive_status(state: str) -> RobotStatus:
    if state == "ready":
         return RobotStatus.READY
    if state == "fault":
         return RobotStatus.FAULT
    if state == str(RobotOperationStates.HOMING):
         return RobotStatus.HOMING
    if state == str(PickAndPlaceStates.COMPLETED):
         return RobotStatus.COMPLETED
    return RobotStatus.RUNNING

def get_current_target(fsm: GantryRobotStateMachine) -> Optional[Vector3]:
    plan = fsm.motion_plan
    if plan is None:
         return None
         
    targets = {
        str(RobotOperationStates.HOMING): plan.home,
        str(PickAndPlaceStates.MOVE_ABOVE_CUBE): plan.above_cube,
        str(PickAndPlaceStates.LOWER_TO_CUBE): plan.cube,
        str(PickAndPlaceStates.LIFT_CUBE): plan.above_cube,
        str(PickAndPlaceStates.MOVE_ABOVE_DESTINATION): plan.above_destination,
        str(PickAndPlaceStates.LOWER_TO_DESTINATION): plan.destination,
        str(PickAndPlaceStates.LIFT_FROM_DESTINATION): plan.above_destination,
    }
    raw = targets.get(fsm.state)
    if raw is None:
         return None
    return Vector3(x=raw[0], y=raw[1], z=raw[2])
