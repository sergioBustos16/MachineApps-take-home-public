import React from "react";
import type { StateTrackerProps } from "../types/telemetry";

interface StateMeta {
  label: string;
  stepIndex: number;
}

const STATE_METADATA: Record<string, StateMeta> = {
  "PickAndPlaceStates_MOVEABOVECUBE": {
    label: "1. Positioning Above Cube",
    stepIndex: 0,
  },
  "PickAndPlaceStates_LOWERTOCUBE": {
    label: "2. Lowering Gantry to Cube",
    stepIndex: 1,
  },
  "PickAndPlaceStates_CLOSEGRIPPER": {
    label: "3. Engaging Gripper Jaws",
    stepIndex: 2,
  },
  "PickAndPlaceStates_LIFTCUBE": {
    label: "4. Lifting Cube to Clearance",
    stepIndex: 3,
  },
  "PickAndPlaceStates_MOVEABOVEDESTINATION": {
    label: "5. Traversing to Destination",
    stepIndex: 4,
  },
  "PickAndPlaceStates_LOWERTODESTINATION": {
    label: "6. Placing Cube at Destination",
    stepIndex: 5,
  },
  "PickAndPlaceStates_OPENGRIPPER": {
    label: "7. Releasing Gripper Jaws",
    stepIndex: 6,
  },
  "PickAndPlaceStates_LIFTFROMDESTINATION": {
    label: "8. Retracting to Safe Height",
    stepIndex: 7,
  },
  "PickAndPlaceStates_COMPLETED": {
    label: "9. Sequence Completed",
    stepIndex: 8,
  },
};

const ORDERED_STATES = [
  "PickAndPlaceStates_MOVEABOVECUBE",
  "PickAndPlaceStates_LOWERTOCUBE",
  "PickAndPlaceStates_CLOSEGRIPPER",
  "PickAndPlaceStates_LIFTCUBE",
  "PickAndPlaceStates_MOVEABOVEDESTINATION",
  "PickAndPlaceStates_LOWERTODESTINATION",
  "PickAndPlaceStates_OPENGRIPPER",
  "PickAndPlaceStates_LIFTFROMDESTINATION",
  "PickAndPlaceStates_COMPLETED",
];

export const StateTracker: React.FC<StateTrackerProps> = ({ state, isStale }) => {
  const currentMetadata = STATE_METADATA[state];
  const activeIndex = currentMetadata ? currentMetadata.stepIndex : -1;

  // Determine if we're in some operation that's not part of the sequence (e.g. ready, homing, fault)
  const isSequenceActive = activeIndex >= 0;

  return (
    <div className="glass-panel" style={{ marginTop: "1rem" }}>
      <h2>Pick &amp; Place Execution</h2>
      <div className="timeline">
        {ORDERED_STATES.map((stateKey) => {
          const stepMeta = STATE_METADATA[stateKey];
          const isActive = state === stateKey && !isStale;
          const isCompleted = isSequenceActive && activeIndex > stepMeta.stepIndex;

          let stepClass = "timeline-step";
          if (isActive) stepClass += " active";
          if (isCompleted) stepClass += " completed";

          return (
            <div key={stateKey} className={stepClass}>
              <div className="step-indicator">
                {isCompleted ? "✓" : stepMeta.stepIndex + 1}
              </div>
              <div className="step-label">{stepMeta.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default StateTracker;
