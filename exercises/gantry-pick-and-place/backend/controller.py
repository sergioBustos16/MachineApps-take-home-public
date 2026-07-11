import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from domain.enums import CubeStatus
from communication.decorators import stream
from gantry_fsm import GantryRobotStateMachine
from configuration_service import ConfigurationService
from telemetry_service import TelemetrySnapshot, Vector3, STATIC_LIMITS, derive_status, get_current_target

logger = logging.getLogger("vention.app.controller")

@stream("telemetry", payload=TelemetrySnapshot, replay=True)
async def publish_telemetry(snapshot: TelemetrySnapshot) -> TelemetrySnapshot:
    """Publishes telemetry frame directly to Vention streams."""
    return snapshot

class RobotController:
    TICK_SECONDS = 0.05
    TELEMETRY_INTERVAL_SECONDS = 0.1

    def __init__(self, state_machine: GantryRobotStateMachine, config_service: ConfigurationService):
        self.state_machine = state_machine
        self.config_service = config_service
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._latest_snapshot: Optional[TelemetrySnapshot] = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
             return
        self._task.cancel()
        try:
             await self._task
        except asyncio.CancelledError:
             pass
        finally:
             self._task = None

    def get_latest_snapshot(self) -> TelemetrySnapshot:
         if self._latest_snapshot is None:
              self._latest_snapshot = self._build_snapshot()
         return self._latest_snapshot

    def _event_signature(self, snapshot: TelemetrySnapshot) -> tuple:
         return (
              snapshot.state,
              snapshot.status,
              snapshot.gripper_state,
              snapshot.cube_status,
              snapshot.last_error.code if snapshot.last_error else None
         )

    def _build_snapshot(self) -> TelemetrySnapshot:
         fsm = self.state_machine
         pos = fsm.robot.get_position()
         vel = fsm.robot.get_velocity()
         
         active_cfg = fsm.execution_config
         saved_cfg = self.config_service.get_cached()
         cfg = active_cfg or saved_cfg
         
         cube_pos = Vector3(x=cfg.cube_position.x, y=cfg.cube_position.y, z=cfg.cube_position.z)
         dest_pos = Vector3(x=cfg.destination_position.x, y=cfg.destination_position.y, z=cfg.destination_position.z)
         if fsm.cube_status == CubeStatus.AT_SOURCE:
              cube_current_pos = cube_pos
         else:
              cube_current_pos = Vector3(
                   x=fsm.cube_current_position[0],
                   y=fsm.cube_current_position[1],
                   z=fsm.cube_current_position[2],
              )
         
         return TelemetrySnapshot(
              timestamp=datetime.now(timezone.utc),
              sequence_id=fsm.active_sequence_id,
              status=derive_status(fsm.state),
              state=fsm.state,
              requires_homing=fsm.requires_homing,
              position=Vector3(x=pos[0], y=pos[1], z=pos[2]),
              velocity=Vector3(x=vel[0], y=vel[1], z=vel[2]),
              target_position=get_current_target(fsm),
              cube_position=cube_pos,
              cube_current_position=cube_current_pos,
              cube_status=fsm.cube_status,
              destination_position=dest_pos,
              workspace_bounds=STATIC_LIMITS,
              gripper_state="CLOSED" if fsm.robot.is_gripper_closed() else "OPEN",
              is_moving=fsm.robot.is_moving(),
              last_error=fsm.last_error
         )

    async def _run(self) -> None:
        last_publish = 0.0
        try:
             # Allow FastAPI and the Vention app enough time to fully finalize streams
             await asyncio.sleep(1.0)
             while self._running:
                 started_at = time.monotonic()
                 
                 # 1. Tick the active state callback
                 self.state_machine.execute_current_callback()
                 
                 # 2. Build immutable snapshot atomically
                 previous_snapshot = self._latest_snapshot
                 snapshot = self._build_snapshot()
                 self._latest_snapshot = snapshot
                 
                 # 3. Publish immediately on transitions or rate-limited at 10Hz
                 is_event_triggered = (
                      previous_snapshot is None or 
                      self._event_signature(previous_snapshot) != self._event_signature(snapshot)
                 )
                 
                 if (started_at - last_publish >= self.TELEMETRY_INTERVAL_SECONDS) or is_event_triggered:
                      try:
                          await publish_telemetry(snapshot)
                      except Exception:
                          logger.warning("Telemetry publication streaming failed.", exc_info=True)
                      last_publish = started_at
                      
                 elapsed = time.monotonic() - started_at
                 await asyncio.sleep(max(0.0, self.TICK_SECONDS - elapsed))
        except asyncio.CancelledError:
             raise
