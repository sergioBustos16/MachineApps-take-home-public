import React, { useState, useEffect } from "react";
import type { ConfigurationFormProps, RobotConfiguration } from "../types/telemetry";

export const ConfigurationForm: React.FC<ConfigurationFormProps> = ({
  savedConfiguration,
  disabled,
  onSave,
}) => {
  const [config, setConfig] = useState<RobotConfiguration>({ ...savedConfiguration });
  const [isSaving, setIsSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Sync state with parent updates
  useEffect(() => {
    setConfig({ ...savedConfiguration });
  }, [savedConfiguration]);

  const handleChange = (
    section: "cube_position" | "destination_position" | "home_position" | null,
    field: string,
    value: string
  ) => {
    const num = parseFloat(value);
    if (section) {
      setConfig((prev) => ({
        ...prev,
        [section]: {
          ...prev[section],
          [field]: isNaN(num) ? value : num,
        },
      }));
    } else {
      setConfig((prev) => ({
        ...prev,
        [field]: isNaN(num) ? value : num,
      }));
    }
  };

  const validate = (): boolean => {
    const limits = { min: -1000, max: 1000 };

    const checkPosition = (pos: any, name: string) => {
      if (typeof pos.x !== "number" || pos.x < limits.min || pos.x > limits.max) return `${name} X must be between ${limits.min} and ${limits.max}`;
      if (typeof pos.y !== "number" || pos.y < limits.min || pos.y > limits.max) return `${name} Y must be between ${limits.min} and ${limits.max}`;
      if (typeof pos.z !== "number" || pos.z < limits.min || pos.z > limits.max) return `${name} Z must be between ${limits.min} and ${limits.max}`;
      return null;
    };

    let err = checkPosition(config.cube_position, "Cube Position");
    if (err) return (setValidationError(err), false);

    err = checkPosition(config.destination_position, "Destination Position");
    if (err) return (setValidationError(err), false);

    err = checkPosition(config.home_position, "Home Position");
    if (err) return (setValidationError(err), false);

    if (typeof config.safe_z !== "number" || config.safe_z < limits.min || config.safe_z > limits.max) {
      return (setValidationError(`Safe Z height must be between ${limits.min} and ${limits.max}`), false);
    }
    if (config.safe_z <= Math.max(config.cube_position.z, config.destination_position.z)) {
      return (setValidationError("Safe Z height must be above both cube and destination Z coordinates"), false);
    }
    if (typeof config.travel_speed !== "number" || config.travel_speed <= 0 || config.travel_speed > 100) {
      return (setValidationError("Travel speed must be greater than 0 and no more than 100 mm/s"), false);
    }
    if (typeof config.home_speed !== "number" || config.home_speed <= 0 || config.home_speed > 100) {
      return (setValidationError("Home speed must be greater than 0 and no more than 100 mm/s"), false);
    }

    setValidationError(null);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSaving(true);
    try {
      await onSave(config);
    } catch (err: any) {
      setValidationError(err.message || "Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  };

  const renderCoordinateInputs = (
    section: "cube_position" | "destination_position" | "home_position",
    title: string
  ) => {
    const position = config[section];
    const axes: Array<{ key: "x" | "y" | "z"; label: string }> = [
      { key: "x", label: "X axis" },
      { key: "y", label: "Y axis" },
      { key: "z", label: "Z axis" },
    ];

    return (
      <div className="form-group">
        <label>{title}</label>
        <div className="input-row coordinate-row">
          {axes.map((axis) => (
            <div className="coordinate-field" key={`${section}-${axis.key}`}>
              <span className="coordinate-label">{axis.label}</span>
              <input
                type="number"
                className="form-input"
                aria-label={`${title} ${axis.label}`}
                disabled={disabled}
                value={position[axis.key]}
                onChange={(e) => handleChange(section, axis.key, e.target.value)}
              />
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <form className="glass-panel" onSubmit={handleSubmit}>
      <h2>Configuration</h2>

      {validationError && (
        <div
          style={{
            background: "rgba(248, 113, 113, 0.1)",
            color: "var(--color-danger)",
            border: "1px solid rgba(248, 113, 113, 0.2)",
            borderRadius: "8px",
            padding: "0.75rem",
            fontSize: "0.85rem",
            marginBottom: "1rem",
            fontWeight: "600",
          }}
        >
          {validationError}
        </div>
      )}

      {renderCoordinateInputs("cube_position", "Cube Position (mm)")}
      {renderCoordinateInputs("destination_position", "Destination Position (mm)")}
      {renderCoordinateInputs("home_position", "Home Position (mm)")}

      {/* Operational Limits */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
        <div className="form-group">
          <label>Safe Z (mm)</label>
          <input
            type="number"
            className="form-input"
            aria-label="Safe Z height"
            disabled={disabled}
            value={config.safe_z}
            onChange={(e) => handleChange(null, "safe_z", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Travel Speed (mm/s)</label>
          <input
            type="number"
            className="form-input"
            aria-label="Travel speed"
            disabled={disabled}
            value={config.travel_speed}
            onChange={(e) => handleChange(null, "travel_speed", e.target.value)}
          />
        </div>
      </div>

      <div className="form-group" style={{ marginBottom: "1.5rem" }}>
        <label>Home Speed (mm/s)</label>
        <input
          type="number"
          className="form-input"
          aria-label="Home speed"
          disabled={disabled}
          value={config.home_speed}
          onChange={(e) => handleChange(null, "home_speed", e.target.value)}
        />
      </div>

      <button
        type="submit"
        className="btn btn-secondary"
        style={{ width: "100%" }}
        disabled={disabled || isSaving}
      >
        {isSaving ? "Saving Configuration..." : "Save Configuration"}
      </button>
    </form>
  );
};
export default ConfigurationForm;
