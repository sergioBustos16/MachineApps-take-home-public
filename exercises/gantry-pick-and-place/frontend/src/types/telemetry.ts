export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface AxisBounds {
  min: number;
  max: number;
}

export interface WorkspaceBounds {
  x: AxisBounds;
  y: AxisBounds;
  z: AxisBounds;
}

export interface StateMachineError {
  code: string;
  message: string;
  state: string;
}

export interface TelemetrySnapshot {
  timestamp: string;
  sequence_id: string | null;
  status: "ready" | "running" | "homing" | "completed" | "fault";
  state: string;
  requires_homing: boolean;
  position: Vector3;
  velocity: Vector3;
  target_position: Vector3 | null;
  cube_position: Vector3;
  cube_current_position: Vector3;
  cube_status: "at_source" | "attached" | "at_destination";
  destination_position: Vector3;
  workspace_bounds: WorkspaceBounds;
  gripper_state: "OPEN" | "CLOSED";
  is_moving: boolean;
  last_error: StateMachineError | null;
}

export interface RobotConfiguration {
  cube_position: Vector3;
  destination_position: Vector3;
  safe_z: number;
  home_position: Vector3;
  travel_speed: number;
  home_speed: number;
}

// Props contracts for component layout
export interface CommandBarProps {
  status: "ready" | "running" | "homing" | "completed" | "fault";
  connectionState: "connecting" | "streaming" | "polling" | "disconnected";
  isStale: boolean;
  requiresHoming: boolean;
  pendingCommand: "start" | "home" | "reset" | null;
  onStart(): Promise<void>;
  onHome(): Promise<void>;
  onReset(): Promise<void>;
}

export interface GantryVisualizerProps {
  telemetry: TelemetrySnapshot;
  safeZ?: number;
}

export interface ConfigurationFormProps {
  savedConfiguration: RobotConfiguration;
  disabled: boolean;
  onSave(config: RobotConfiguration): Promise<void>;
}

export interface StateTrackerProps {
  state: string;
  isStale: boolean;
}
export interface StatusBadgeProps {
  status: "ready" | "running" | "homing" | "completed" | "fault";
  connectionState: "connecting" | "streaming" | "polling" | "disconnected";
  isStale: boolean;
}
