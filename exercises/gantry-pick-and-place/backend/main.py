import os
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from communication.app import VentionApp
from storage.bootstrap import bootstrap
from database import ConfigurationRecord, ConfigurationRepository
from configuration_service import ConfigurationService
from robot_sim import Robot
from robot_adapter import RobotAdapter
from gantry_fsm import GantryRobotStateMachine
from controller import RobotController
from domain.exceptions import RobotBusyError, FaultResetError
from domain.models import RobotConfiguration

DEFAULT_DATABASE_URL = "sqlite:///./gantry_robot.db"

class AppContainer:
    def __init__(self):
        self.robot_sim = Robot()
        self.robot_adapter = RobotAdapter(self.robot_sim)
        self.state_machine = GantryRobotStateMachine(self.robot_adapter)
        
        from storage.accessor import ModelAccessor
        self.config_accessor = ModelAccessor(ConfigurationRecord, component_name="configuration")
        self.config_repo = ConfigurationRepository(self.config_accessor)
        self.config_service = ConfigurationService(self.config_repo)
        self.robot_controller = RobotController(self.state_machine, self.config_service)

container: Optional[AppContainer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global container
    container = AppContainer()
    
    # Bootstrap storage accessors
    bootstrap(
        app=app,
        accessors=[container.config_accessor],
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        create_tables=True,
        enable_db_router=False
    )
    
    # Pre-cache database configuration inside the service on startup
    await container.config_service.get()
    
    # Start background 20Hz controller task
    await container.robot_controller.start()
    yield
    # Graceful shutdown of loop tasks
    await container.robot_controller.stop()

app = VentionApp("GantryRobot", title="GantryRobot", service_name="GantryRobot", lifespan=lifespan)

@app.exception_handler(RobotBusyError)
async def handle_busy_error(request, exc):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": {"code": "ROBOT_BUSY", "message": str(exc)}}
    )

@app.exception_handler(FaultResetError)
async def handle_reset_error(request, exc):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": {"code": "FAULT_RESET_FAILED", "message": str(exc)}}
    )

@app.get("/api/configuration", response_model=RobotConfiguration)
async def get_configuration():
    if container is None:
         raise HTTPException(status_code=503, detail="Application container not initialized")
    return await container.config_service.get()

@app.put("/api/configuration", response_model=RobotConfiguration)
async def update_configuration(config: RobotConfiguration):
    if container is None:
         raise HTTPException(status_code=503, detail="Application container not initialized")
    if container.state_machine.state != "ready":
         raise RobotBusyError("Configuration cannot be updated while the robot is active")
    return await container.config_service.update(config)

@app.get("/api/telemetry")
async def get_telemetry():
    if container is None:
         raise HTTPException(status_code=503, detail="Application container not initialized")
    return container.robot_controller.get_latest_snapshot()

@app.post("/api/commands/start", status_code=status.HTTP_202_ACCEPTED)
async def start_sequence():
    if container is None:
         raise HTTPException(status_code=503, detail="Application container not initialized")
    config = await container.config_service.get()
    seq_id = container.state_machine.start_sequence(config)
    return {
        "accepted": True, 
        "command": "start", 
        "sequence_id": seq_id, 
        "state": container.state_machine.state
    }

@app.post("/api/commands/home", status_code=status.HTTP_202_ACCEPTED)
async def start_homing():
    if container is None:
         raise HTTPException(status_code=503, detail="Application container not initialized")
    config = await container.config_service.get()
    seq_id = container.state_machine.start_homing(config)
    return {
        "accepted": True, 
        "command": "home", 
        "sequence_id": seq_id, 
        "state": container.state_machine.state
    }

@app.post("/api/commands/reset", status_code=status.HTTP_200_OK)
async def reset_fault():
    if container is None:
         raise HTTPException(status_code=503, detail="Application container not initialized")
    container.state_machine.reset_fault()
    return {
        "accepted": True, 
        "command": "reset", 
        "state": "ready", 
        "requiresHoming": True
    }

# Finalize the VentionApp to compile all actions/streams and enable telemetry streaming
app.finalize()
