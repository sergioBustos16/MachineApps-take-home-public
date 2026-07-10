import math
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator
from domain.enums import RobotStatus, CubeStatus

WORKSPACE_LIMIT_MIN = -1000.0
WORKSPACE_LIMIT_MAX = 1000.0

class Position(BaseModel):
    x: float
    y: float
    z: float

class RobotConfiguration(BaseModel):
    cube_position: Position
    destination_position: Position
    safe_z: float
    home_position: Position
    travel_speed: float = 90.0
    home_speed: float = 50.0

    @model_validator(mode="after")
    def validate_motion_configuration(self):
        # 1. Safe Z clearance rule
        if self.safe_z <= max(self.cube_position.z, self.destination_position.z):
            raise ValueError("safe_z must be above both cube and destination Z coordinates")
        
        # 2. Travel speed rules (verified limit: 0 to 100 mm/s)
        if not (0 < self.travel_speed <= 100) or not (0 < self.home_speed <= 100):
             raise ValueError("Speeds must be between 0 and 100 mm/s inclusive")
        
        # 3. Workspace bounds and finiteness rules
        for pos in (self.cube_position, self.destination_position, self.home_position):
             self._validate_position_bounds(pos)
        
        if not (WORKSPACE_LIMIT_MIN <= self.safe_z <= WORKSPACE_LIMIT_MAX):
             raise ValueError("Safe Z height is outside workspace boundaries")
             
        # 4. Identity rule
        if self.cube_position == self.destination_position:
             raise ValueError("Cube and destination coordinates cannot be identical")
             
        return self

    def _validate_position_bounds(self, pos: Position):
        coords = (pos.x, pos.y, pos.z)
        if not all(math.isfinite(c) for c in coords):
             raise ValueError("Coordinates must be finite real numbers")
        for axis, val in [("X", pos.x), ("Y", pos.y), ("Z", pos.z)]:
             if not (WORKSPACE_LIMIT_MIN <= val <= WORKSPACE_LIMIT_MAX):
                  raise ValueError(f"{axis} position of {val} is outside valid limits [-1000, 1000]")

class MotionPlan(BaseModel):
    home: tuple[float, float, float]
    cube: tuple[float, float, float]
    above_cube: tuple[float, float, float]
    destination: tuple[float, float, float]
    above_destination: tuple[float, float, float]
    travel_speed: float
    home_speed: float

    @classmethod
    def from_config(cls, config: RobotConfiguration) -> "MotionPlan":
        return cls(
            home=(config.home_position.x, config.home_position.y, config.home_position.z),
            cube=(config.cube_position.x, config.cube_position.y, config.cube_position.z),
            above_cube=(config.cube_position.x, config.cube_position.y, config.safe_z),
            destination=(config.destination_position.x, config.destination_position.y, config.destination_position.z),
            above_destination=(config.destination_position.x, config.destination_position.y, config.safe_z),
            travel_speed=config.travel_speed,
            home_speed=config.home_speed,
        )

class Vector3(BaseModel):
    x: float
    y: float
    z: float

class AxisBounds(BaseModel):
    min: float
    max: float

class WorkspaceBounds(BaseModel):
    x: AxisBounds
    y: AxisBounds
    z: AxisBounds

class StateMachineError(BaseModel):
    code: str
    message: str
    state: str

class TelemetrySnapshot(BaseModel):
    timestamp: datetime
    sequence_id: Optional[str] = None
    status: RobotStatus
    state: str
    requires_homing: bool
    
    position: Vector3
    velocity: Vector3
    target_position: Optional[Vector3] = None
    
    cube_position: Vector3
    cube_current_position: Vector3
    cube_status: CubeStatus
    destination_position: Vector3
    workspace_bounds: WorkspaceBounds
    
    gripper_state: str
    is_moving: bool
    last_error: Optional[StateMachineError] = None
