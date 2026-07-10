from enum import Enum

class RobotStatus(str, Enum):
    READY = "ready"
    RUNNING = "running"
    HOMING = "homing"
    COMPLETED = "completed"
    FAULT = "fault"

class CubeStatus(str, Enum):
    AT_SOURCE = "at_source"
    ATTACHED = "attached"
    AT_DESTINATION = "at_destination"
