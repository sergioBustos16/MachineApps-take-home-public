class RobotBusyError(Exception):
    """Raised when commands are sent to the state machine while it is not ready."""
    pass

class FaultResetError(Exception):
    """Raised when attempting to reset the FSM from a non-FAULT state."""
    pass
