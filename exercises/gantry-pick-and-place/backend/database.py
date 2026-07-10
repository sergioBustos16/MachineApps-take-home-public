from typing import Optional
from sqlmodel import SQLModel, Field
from domain.models import RobotConfiguration, Position

class ConfigurationRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=1, primary_key=True)
    cube_x: float = 200.0
    cube_y: float = 200.0
    cube_z: float = 0.0
    dest_x: float = 800.0
    dest_y: float = 800.0
    dest_z: float = 0.0
    safe_z: float = 500.0
    home_x: float = 0.0
    home_y: float = 0.0
    home_z: float = 0.0
    travel_speed: float = 90.0
    home_speed: float = 50.0

class ConfigurationRepository:
    def __init__(self, accessor):
        self._accessor = accessor

    def _to_domain(self, record: ConfigurationRecord) -> RobotConfiguration:
        return RobotConfiguration(
            cube_position=Position(x=record.cube_x, y=record.cube_y, z=record.cube_z),
            destination_position=Position(x=record.dest_x, y=record.dest_y, z=record.dest_z),
            safe_z=record.safe_z,
            home_position=Position(x=record.home_x, y=record.home_y, z=record.home_z),
            travel_speed=record.travel_speed,
            home_speed=record.home_speed
        )

    def _to_record(self, config: RobotConfiguration) -> ConfigurationRecord:
        return ConfigurationRecord(
            id=1,
            cube_x=config.cube_position.x,
            cube_y=config.cube_position.y,
            cube_z=config.cube_position.z,
            dest_x=config.destination_position.x,
            dest_y=config.destination_position.y,
            dest_z=config.destination_position.z,
            safe_z=config.safe_z,
            home_x=config.home_position.x,
            home_y=config.home_position.y,
            home_z=config.home_position.z,
            travel_speed=config.travel_speed,
            home_speed=config.home_speed
        )

    def get_or_create(self) -> RobotConfiguration:
        record = self._accessor.get(1)
        if record is None:
            record = ConfigurationRecord()
            self._accessor.insert(record)
        return self._to_domain(record)

    def save(self, config: RobotConfiguration) -> RobotConfiguration:
        record = self._to_record(config)
        self._accessor.save(record, actor="Operator")
        return config
