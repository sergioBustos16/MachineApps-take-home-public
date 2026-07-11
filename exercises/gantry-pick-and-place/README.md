# Gantry Pick & Place Solution

This implementation is a proof-of-concept 3-axis gantry pick-and-place simulator for the Vention take-home exercise. 
It uses a FastAPI backend with Vention communication, state-machine, and storage libraries, plus a React/TypeScript frontend for configuration, telemetry, controls, and visualization.

## Quick Start: Local Development

Use PowerShell from the exercise folder:

```powershell
cd C:\Users\sergo\Documents\dev\MachineApps-take-home-public\exercises\gantry-pick-and-place
```

Check the installed tools:

```powershell
python --version
py --version
node --version
npm --version
docker --version
```

Required backend runtime: Python 3.10. The Vention packages used by this exercise declare support for Python >=3.10,<3.11. Use Docker if Python 3.10 is not installed locally. Recommended frontend runtime: Node.js 20+.

### Backend

```powershell
cd C:\Users\sergo\Documents\dev\MachineApps-take-home-public
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
cd .\exercises\gantry-pick-and-place\backend
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend exposes:

- `GET /api/configuration` for saved robot/cube/destination settings.
- `PUT /api/configuration` for updating settings while the robot is ready.
- `GET /api/telemetry` for the latest robot telemetry snapshot.
- `POST /api/commands/home` to move to the configured home position.
- `POST /api/commands/start` to run the pick-and-place sequence.
- `POST /api/commands/reset` to reset from a fault state.

### Frontend

Open a second PowerShell window:

```powershell
cd C:\Users\sergo\Documents\dev\MachineApps-take-home-public\exercises\gantry-pick-and-place\frontend
npm install
npm run dev
```

Open the app at:

```text
http://localhost:3000
```

## How To Use The App

1. Start the backend and frontend.
2. Confirm the dashboard shows robot position, cube position, destination, gripper state, motion status, and current FSM state.
3. Adjust cube, destination, home, safe Z, and speed values if needed.
4. Click `Home Gantry` first. The backend intentionally blocks `Start Sequence` until homing succeeds.
5. Click `Start Sequence`.
6. Watch the sequence: move above cube, lower, close gripper, lift, move above destination, lower, open gripper, and lift away.

## Docker

To run the full stack with one command:

```powershell
cd C:\Users\sergo\Documents\dev\MachineApps-take-home-public\exercises\gantry-pick-and-place
docker compose up --build
```

Open:

```text
http://localhost:3000
```

The Docker backend reads `DATABASE_URL` from `docker-compose.yml`, so the SQLite database is stored in the configured Docker volume.

## Design Decisions

- The backend owns robot state, cube attachment, gripper state, and sequence progression so the frontend cannot visually jump ahead of the simulated robot.
- The FSM callbacks repeatedly call `robot_sim.py` movement methods until motion completes, matching the exercise requirement.
- Homing is required before starting a sequence and after fault reset. This makes the demo flow explicit and keeps recovery deterministic.
- Configuration is persisted with `vention-storage` and served through the backend, while telemetry is available through both Vention streaming and HTTP polling fallback.
- Frontend validation mirrors backend and simulator limits: coordinates are bounded to `[-1000, 1000]`, speeds must be greater than `0` and no more than `100`, and safe Z must be above cube and destination Z.

## Verification

Run backend checks:

```powershell
cd C:\Users\sergo\Documents\dev\MachineApps-take-home-public
.\.venv\Scripts\Activate.ps1
cd .\exercises\gantry-pick-and-place\backend
pytest
```

Run frontend checks:

```powershell
cd C:\Users\sergo\Documents\dev\MachineApps-take-home-public\exercises\gantry-pick-and-place\frontend
npm run build
```

Manual acceptance test:

- Save a valid configuration.
- Home the gantry.
- Start the sequence.
- Confirm the robot completes the full pick-and-place path and returns to ready.
- Confirm invalid speeds over `100` or unsafe safe-Z values are rejected before save.

## Original Exercise Requirements
# **Robot Pick & Place Simulation**

## **Problem Statement**

You are tasked with building a proof-of-concept for a 3-axis gantry robot solution. The goal is to implement a Python backend that controls a robotic arm using a State Machine and a React frontend to visualize and configure the operation.

You must simulate a "Pick and Place" sequence: picking a cube from **Table A** and placing it on **Table B** within the provided application footprint.

![image](https://github.com/VentionCoExperiments/MachineApps-take-home-public/raw/main/exercises/gantry-pick-and-place/figure1_application_footprint.png)

## **Checklist of Requirements**

### **Mandatory Requirements**

**Backend (Python & FastAPI)**

  - [ ] **Communication Framework:** Use the [`vention-communication`](https://pypi.org/project/vention-communication/) library to establish communication between the frontend and backend.
  - [ ] **State Machine Integration:** Implement the robot's control logic using the [`vention-state-machine`](https://pypi.org/project/vention-state-machine/) library.
  - [ ] **Robot Simulation:** Interface with the provided `robot_sim.py` class.
      - *Note:* The `move_to` method must be called repeatedly until motion is complete. This should be handled inside your state machine callbacks.
  - [ ] **API Endpoints:** Create endpoints to:
      - Get/Set robot, cube, and destination positions.
      - specific commands: `Home Robot`, `Start Sequence`, `Get Status`.
      - *Note:* The "Home" operation moves the robot to its home position (default: `[0, 0, 0]`). Review `robot_sim.py` to understand the `move_home()` method and the `home_position` parameter.
  - [ ] **Logic:** Implement the full Pick-and-Place sequence:
    1.  Move to Cube (Table A) $\rightarrow$ Lower $\rightarrow$ Close Gripper.
    2.  Lift $\rightarrow$ Move to Destination (Table B).
    3.  Lower $\rightarrow$ Open Gripper $\rightarrow$ Lift.

**Frontend (React & TypeScript)**

  - [ ] **Dashboard:** Display real-time telemetry:
      - Current Robot Position (X, Y, Z).
      - Cube Start Position & Destination.
      - Robot Status (Gripper open/closed, moving/idle).
      - Current State of the State Machine.
  - [ ] **Controls:** Allow the user to:
      - Configure the Cube's start coordinates and destination coordinates.
      - Trigger the "Home" operation (moves robot to home position, default: `[0, 0, 0]`).
      - Start the "Pick and Place" sequence.
  - [ ] **Visuals:** Provide a clear visual indication of errors and operational state.

### **Bonus Points**

  - [ ] **Persistence:** Use [`vention-storage`](https://pypi.org/project/vention-storage/) to save configuration (e.g., cube locations) between restarts.
  - [ ] **Testing:** Write unit tests for the backend logic or component tests for the frontend.
  - [ ] **Containerization:** Run the whole stack (Backend + Frontend) with a single command (e.g., Docker Compose).
  - [ ] **Demo:** Include a short video recording of your solution in action.

## **Technical Resources**

**Backend Setup**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Requirements include: fastapi, vention-communication==0.3.0, vention-state-machine==0.3.1, vention-storage==0.5.4
```

**Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

## **Submission**

  - [ ] Fork the repository and complete the work in your fork.
  - [ ] Include a **README** documenting:
      - Setup and run instructions.
      - Design decisions, assumptions, and trade-offs.
  - [ ] Push your changes and share the repository link.

-----

### **Questions?**

If you have any questions about the exercise, please contact [isaac.mills@vention.cc](mailto:isaac.mills@vention.cc). Happy coding\!
