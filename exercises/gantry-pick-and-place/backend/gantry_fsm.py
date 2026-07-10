import time
import logging
from uuid import uuid4
from typing import Optional
from state_machine.defs import State, StateGroup
from state_machine.core import StateMachine, BaseStates, BaseTriggers
from robot_adapter import RobotAdapter
from domain.exceptions import RobotBusyError, FaultResetError
from domain.enums import CubeStatus
from domain.models import RobotConfiguration, MotionPlan, StateMachineError

logger = logging.getLogger("vention.app.state_machine")

MOTION_TIMEOUT_SECONDS = 10.0
COMPLETION_HOLD_SECONDS = 1.0

class RobotOperationStates(StateGroup):
    HOMING = State()

class PickAndPlaceStates(StateGroup):
    MOVEABOVECUBE = State()
    LOWERTOCUBE = State()
    CLOSEGRIPPER = State()
    LIFTCUBE = State()
    MOVEABOVEDESTINATION = State()
    LOWERTODESTINATION = State()
    OPENGRIPPER = State()
    LIFTFROMDESTINATION = State()
    COMPLETED = State()

class RobotStates:
    operations = RobotOperationStates()
    sequence = PickAndPlaceStates()

class GantryRobotStateMachine(StateMachine):
    def __init__(self, robot_adapter: RobotAdapter, **kwargs):
        self.robot = robot_adapter
        self.execution_config: Optional[RobotConfiguration] = None
        self.motion_plan: Optional[MotionPlan] = None
        self.last_error: Optional[StateMachineError] = None
        self.active_sequence_id: Optional[str] = None
        
        # Operational security flags
        self.requires_homing: bool = True

        # Cube physical status tracking
        self.cube_status: CubeStatus = CubeStatus.AT_SOURCE
        self.cube_current_position: tuple[float, float, float] = (0.0, 0.0, 0.0)

        # State timing controls
        self._state_started_at: Optional[float] = None
        self._last_ticked_state: Optional[str] = None

        transitions = [
            {"trigger": "start", "source": BaseStates.READY.value, "dest": str(PickAndPlaceStates.MOVEABOVECUBE)},
            {"trigger": "home", "source": BaseStates.READY.value, "dest": str(RobotOperationStates.HOMING)},
            
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.MOVEABOVECUBE), "dest": str(PickAndPlaceStates.LOWERTOCUBE)},
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.LOWERTOCUBE), "dest": str(PickAndPlaceStates.CLOSEGRIPPER)},
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.CLOSEGRIPPER), "dest": str(PickAndPlaceStates.LIFTCUBE)},
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.LIFTCUBE), "dest": str(PickAndPlaceStates.MOVEABOVEDESTINATION)},
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.MOVEABOVEDESTINATION), "dest": str(PickAndPlaceStates.LOWERTODESTINATION)},
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.LOWERTODESTINATION), "dest": str(PickAndPlaceStates.OPENGRIPPER)},
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.OPENGRIPPER), "dest": str(PickAndPlaceStates.LIFTFROMDESTINATION)},
            {"trigger": "step_completed", "source": str(PickAndPlaceStates.LIFTFROMDESTINATION), "dest": str(PickAndPlaceStates.COMPLETED)},
            
            {"trigger": "sequence_finished", "source": str(PickAndPlaceStates.COMPLETED), "dest": BaseStates.READY.value},
            {"trigger": "home_completed", "source": str(RobotOperationStates.HOMING), "dest": BaseStates.READY.value},
        ]

        super().__init__(
            states=RobotStates,
            transitions=transitions,
            **kwargs
        )

        self._tick_handlers = {
            str(RobotOperationStates.HOMING): self._tick_homing,
            str(PickAndPlaceStates.MOVEABOVECUBE): self._tick_move_above_cube,
            str(PickAndPlaceStates.LOWERTOCUBE): self._tick_lower_to_cube,
            str(PickAndPlaceStates.CLOSEGRIPPER): self._tick_close_gripper,
            str(PickAndPlaceStates.LIFTCUBE): self._tick_lift_cube,
            str(PickAndPlaceStates.MOVEABOVEDESTINATION): self._tick_move_above_destination,
            str(PickAndPlaceStates.LOWERTODESTINATION): self._tick_lower_to_destination,
            str(PickAndPlaceStates.OPENGRIPPER): self._tick_open_gripper,
            str(PickAndPlaceStates.LIFTFROMDESTINATION): self._tick_lift_from_destination,
            str(PickAndPlaceStates.COMPLETED): self._tick_completed,
        }

    def start_sequence(self, config: RobotConfiguration) -> str:
        self._require_ready()
        if self.requires_homing:
             raise RobotBusyError("Command rejected: Gantry must be homed before initiating sequence")

        execution_config = config.model_copy(deep=True)
        motion_plan = MotionPlan.from_config(execution_config)
        
        self.last_error = None
        self.active_sequence_id = str(uuid4())
        self.execution_config = execution_config
        self.motion_plan = motion_plan
        self.cube_status = CubeStatus.AT_SOURCE
        self.cube_current_position = motion_plan.cube
        
        self.trigger("start")
        return self.active_sequence_id

    def start_homing(self, config: RobotConfiguration) -> str:
        self._require_ready()
        execution_config = config.model_copy(deep=True)
        motion_plan = MotionPlan.from_config(execution_config)
        
        self.robot.set_home_position(motion_plan.home)
        self.last_error = None
        self.active_sequence_id = str(uuid4())
        self.execution_config = execution_config
        self.motion_plan = motion_plan
        
        self.trigger("home")
        return self.active_sequence_id

    def reset_fault(self) -> None:
        if self.state != BaseStates.FAULT.value:
            raise FaultResetError(f"Reset command rejected: state is {self.state}, not FAULT")
        self.last_error = None
        self.execution_config = None
        self.motion_plan = None
        self.active_sequence_id = None
        self.requires_homing = True # Safety homing mandatory after soft resets
        self._reset_tick_tracking()
        
        self.trigger(BaseTriggers.RESET.value)

    def execute_current_callback(self) -> None:
        current = self.state
        if current in (BaseStates.READY.value, BaseStates.FAULT.value):
            self._reset_tick_tracking()
            return

        self._track_state_entry(current)
        
        if self.cube_status == CubeStatus.ATTACHED:
             self.cube_current_position = self.robot.get_position()

        handler = self._tick_handlers.get(current)
        if handler is None:
            self._enter_fault(RuntimeError(f"No tick handler registered for state {current}"))
            return

        try:
            self._ensure_not_timed_out(current)
            handler()
        except Exception as exc:
            self._enter_fault(exc)

    def _require_ready(self) -> None:
        if self.state != BaseStates.READY.value:
            raise RobotBusyError(f"Robot is busy; current state is {self.state}")

    def _require_motion_plan(self) -> MotionPlan:
        if self.motion_plan is None:
            raise RuntimeError(f"Safety constraint: MotionPlan is missing in state {self.state}")
        return self.motion_plan

    def _ensure_not_timed_out(self, current: str) -> None:
        if current == str(PickAndPlaceStates.COMPLETED):
            return
        if self._state_started_at is not None:
            if time.monotonic() - self._state_started_at > MOTION_TIMEOUT_SECONDS:
                raise TimeoutError(f"State {current} timed out after {MOTION_TIMEOUT_SECONDS}s")

    def _track_state_entry(self, state: str) -> None:
        if self._state_started_at is None or state != self._last_ticked_state:
            self._state_started_at = time.monotonic()
            self._last_ticked_state = state

    def _reset_tick_tracking(self) -> None:
        self._state_started_at = None
        self._last_ticked_state = None

    def _complete_active_operation(self) -> None:
        self.execution_config = None
        self.motion_plan = None

    def _enter_fault(self, exc: Exception) -> None:
        self.last_error = self._build_error(exc)
        logger.error("FSM fault in state %s: %s", self.state, exc, exc_info=(type(exc), exc, exc.__traceback__))
        try:
            self.trigger(BaseTriggers.TO_FAULT.value)
        except Exception:
            logger.exception("Failed to trigger wildcard to_fault transition")

    def _build_error(self, exc: Exception) -> StateMachineError:
        if isinstance(exc, TimeoutError):
            code = "MOTION_TIMEOUT"
        elif isinstance(exc, RuntimeError) and "Safety constraint" in str(exc):
            code = "MISSING_MOTION_PLAN"
        else:
            code = "STATE_MACHINE_ERROR"
        return StateMachineError(code=code, message=str(exc), state=self.state)

    # ---------- Handlers ----------

    def _tick_homing(self) -> None:
        plan = self._require_motion_plan()
        if self.robot.move_home(speed=plan.home_speed):
            self.requires_homing = False # Homing completed successfully
            self._complete_active_operation()
            self.trigger("home_completed")

    def _tick_move_above_cube(self) -> None:
        plan = self._require_motion_plan()
        if self.robot.move_to(plan.above_cube, speed=plan.travel_speed):
            self.trigger("step_completed")

    def _tick_lower_to_cube(self) -> None:
        plan = self._require_motion_plan()
        if self.robot.move_to(plan.cube, speed=plan.travel_speed):
            self.trigger("step_completed")

    def _tick_close_gripper(self) -> None:
        self.robot.close_gripper()
        self.cube_status = CubeStatus.ATTACHED
        self.trigger("step_completed")

    def _tick_lift_cube(self) -> None:
        plan = self._require_motion_plan()
        if self.robot.move_to(plan.above_cube, speed=plan.travel_speed):
            self.trigger("step_completed")

    def _tick_move_above_destination(self) -> None:
        plan = self._require_motion_plan()
        if self.robot.move_to(plan.above_destination, speed=plan.travel_speed):
            self.trigger("step_completed")

    def _tick_lower_to_destination(self) -> None:
        plan = self._require_motion_plan()
        if self.robot.move_to(plan.destination, speed=plan.travel_speed):
            self.trigger("step_completed")

    def _tick_open_gripper(self) -> None:
        self.robot.open_gripper()
        plan = self._require_motion_plan()
        self.cube_status = CubeStatus.AT_DESTINATION
        self.cube_current_position = plan.destination
        self.trigger("step_completed")

    def _tick_lift_from_destination(self) -> None:
        plan = self._require_motion_plan()
        if self.robot.move_to(plan.above_destination, speed=plan.travel_speed):
            self.trigger("step_completed")

    def _tick_completed(self) -> None:
        if self._state_started_at is not None:
            if time.monotonic() - self._state_started_at >= COMPLETION_HOLD_SECONDS:
                self._complete_active_operation()
                self.trigger("sequence_finished")
