# Gantry Pick & Place Solution

This implementation is a proof-of-concept of a 3-axis gantry pick-and-place simulator for the Vention take-home exercise. 
It uses a FastAPI backend with Vention communication, state-machine, and storage libraries, plus a React/TypeScript frontend for configuration, telemetry, controls, and visualization.

## Quick Start: Local Development

Use PowerShell from the exercise folder:

```powershell
cd MachineApps-take-home-public\exercises\gantry-pick-and-place
```

Check the installed tools:

```powershell
python --version
py --version
node --version 
npm --version
docker --version
```

Required backend runtime: Python 3.10. The Vention packages used by this exercise declare support for Python >=3.10,<3.11 Recommended frontend runtime: Node.js 20.

### Backend

```powershell
#On your root folder run
# Get the env ready with python 3.10
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
# Install dependencies
cd .\exercises\gantry-pick-and-place\backend
python -m pip install --upgrade pip
pip install -r requirements.txt
# you can run pytest to make sure the libraries were propertly installed by running the test cases
pytest
# start your backend on port 8000
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
cd exercises\gantry-pick-and-place\frontend
# Install dependencies
npm install
# Start server, frontend is already configures to start on port 3000
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
cd MachineApps-take-home-public\exercises\gantry-pick-and-place
# you can do it step by step by building first then running, sometimes we only build to check image integrity or visible problems
docker compose build
# then run the containers with
docker compose up -d
# or there is a single command that do both build and run
docker compose up -d --build
```

Open:

```text
http://localhost:3000
```

The Docker backend reads `DATABASE_URL` from `docker-compose.yml`, so the SQLite database is stored in the configured Docker volume.

## Design Decisions
For this POC I consider I tried to achieve realibalbity, division of responsabilities, fault tolerance, speed and compliance. I started by thinking of how to safely store the condiguration and avoid users from making changes once there is an active process. Also how would I effectively divide who is in charge of what part of the system and what the limits should be. O I came up with...

**Backend**
- The backend owns robot state, cube attachment, gripper state, and sequence progression so the frontend cannot visually jump ahead of the simulated robot (this make the backend the source of turth).
- The FSM callbacks repeatedly call `robot_sim.py` movement methods until motion completes, matching the exercise requirement.
  - I decided to go with 9 sequential states to properly track the movement of the robot, these states are (moveAboveCube, LoweToCube, openGriper, CloseGriper, LiftCube, moveAboveDestination, LowerToDestination, liftFromDestination) + the base states such as (homing, completed, fault) this would ensure full traceability, In the case of an error, the operator wouldn't see a generic Failure error but instead a proper sttate of where the robot stopped prventing guessing the failure.
- In security Homing is required before starting a sequence and after fault reset. This makes the demo flow explicit and keeps recovery deterministic.
- Configuration is persisted with `vention-storage` and served through the backend, while telemetry is available through both Vention streaming and HTTP polling fallback. Also, for this POC I introduced an improvement in memory, while having a high frequency updates between the server and the frontend getting the data from the disk would add variable milisecond to the process which can introduce latency issues and more considering a real time 20Hz controller loop., I decided for this POC to use the RAM memory as a quick storage for configuration, meaning if we save the cube axis, destination position and home position on DB at the same time it write to the memory so when we excecute the sequence it will be a matter of microseconds of always knowing where the robot is heading to. Every time we make an update to the config the memory updates the config aswell. This give us the best of both worlds... persistance with SQLite and the timing precision thank to the RAM memory.
- One of the strict rules is that coordinates configurations cannot change while the robot has an active process, in this case even if someone bypasses the frontend and sends a request the FSM will reeject the modification while there is an active movement state, this would protect the robot from changes that may affect the regular opperations
- For safety and fault tolerance I defined a 60 second timeout per state which came from calcualting the average speed of 50mm/s and the size of the canvas of [-1000, 1000], If the robot has to come from the limit to [0,0,0] it would take it 20 seconds but configuration and real world cases are not as perfect as these found in POCs, I decided a buffer of 3 times the expected ensuring flexiblity but also guaranteeing that if the robot go over this time the system can safely transition into fault and halt a possible inifinity movement.
**Frontend**
- For the frontend I decided to go with a dual 2D view to be able to see the precise movement of X-Y on one side and X-Z on the other in this way we can see the exact alilignment down to the pixel.
- Frontend validation mirrors backend and simulator limits: coordinates are bounded to `[-1000, 1000]`, speeds must be greater than `0` and no more than `100`, and safe Z must be above cube and destination Z.


# Trade offs

- One of the trade offs was the refresh rate, I decided to keep it at 10hz, which means 10 telemetry messages per second to save on resources but for critical operation like when the gripper hold the object it goes up to 20Hz or 20 messages per second to have the simulation in the frontend as smooth as possible. Why 20Hz or 10Hz and not 1Hz or 100Hz, 1Hz would be too low it would lag, 100Hz would be a waste of network bandwidth and resources for this specific POC. 
- I choose not to build a complex real-time 3D collision avoidance to detect if the physical metal arm intersects with the objects or the environment, to keep the POC on scope and focus more on the proper handling of the state maching. By making the Finite state machine strictly lift the vertical axis to the safe zone Z, before initiating any other movement in an active state.

## Verification

Run backend checks:

```powershell
cd MachineApps-take-home-public
.\.venv\Scripts\Activate.ps1
cd exercises\gantry-pick-and-place\backend
pytest
```

Run frontend checks:

```powershell
cd MachineApps-take-home-public\exercises\gantry-pick-and-place\frontend
npm run build
```

Manual acceptance test:

- Save a valid configuration.
  - Protect the system from changes in configuration once there is an active process
- Home the gantry.
  - robot must respect the z zone to avoid collitions then move to the home coordinates
- Start the sequence.
  - We should be able to start a new sequence with the provided configuration
- Confirm the robot completes the full pick-and-place path and returns to ready.
  - In this step we validate that the robot is able to respect z zones
  - We validate robot is able to grab the object and drop it at final coordinates
- Confirm invalid speeds over `100` or unsafe safe-Z values are rejected before save.

# DEMO video
[Google Drive video](https://drive.google.com/file/d/1UZ--lJ_QPY_Kvy7L7rBqCrKEoLHKyyeX/view?usp=sharing)

## Original Exercise Requirements
# **Robot Pick & Place Simulation**

## **Problem Statement**

You are tasked with building a proof-of-concept for a 3-axis gantry robot solution. The goal is to implement a Python backend that controls a robotic arm using a State Machine and a React frontend to visualize and configure the operation.

You must simulate a "Pick and Place" sequence: picking a cube from **Table A** and placing it on **Table B** within the provided application footprint.

![image](https://github.com/VentionCoExperiments/MachineApps-take-home-public/raw/main/exercises/gantry-pick-and-place/figure1_application_footprint.png)

## **Checklist of Requirements**

### **Mandatory Requirements**

**Backend (Python & FastAPI)**

  - [x] **Communication Framework:** Use the [`vention-communication`](https://pypi.org/project/vention-communication/) library to establish communication between the frontend and backend.
  - [x] **State Machine Integration:** Implement the robot's control logic using the [`vention-state-machine`](https://pypi.org/project/vention-state-machine/) library.
  - [x] **Robot Simulation:** Interface with the provided `robot_sim.py` class.
      - *Note:* The `move_to` method must be called repeatedly until motion is complete. This should be handled inside your state machine callbacks.
  - [x] **API Endpoints:** Create endpoints to:
      - Get/Set robot, cube, and destination positions.
      - specific commands: `Home Robot`, `Start Sequence`, `Get Status`.
      - *Note:* The "Home" operation moves the robot to its home position (default: `[0, 0, 0]`). Review `robot_sim.py` to understand the `move_home()` method and the `home_position` parameter.
  - [x] **Logic:** Implement the full Pick-and-Place sequence:
    1.  Move to Cube (Table A) $\rightarrow$ Lower $\rightarrow$ Close Gripper.
    2.  Lift $\rightarrow$ Move to Destination (Table B).
    3.  Lower $\rightarrow$ Open Gripper $\rightarrow$ Lift.

**Frontend (React & TypeScript)**

  - [x] **Dashboard:** Display real-time telemetry:
      - Current Robot Position (X, Y, Z).
      - Cube Start Position & Destination.
      - Robot Status (Gripper open/closed, moving/idle).
      - Current State of the State Machine.
  - [x] **Controls:** Allow the user to:
      - Configure the Cube's start coordinates and destination coordinates.
      - Trigger the "Home" operation (moves robot to home position, default: `[0, 0, 0]`).
      - Start the "Pick and Place" sequence.
  - [x] **Visuals:** Provide a clear visual indication of errors and operational state.

### **Bonus Points**

  - [x] **Persistence:** Use [`vention-storage`](https://pypi.org/project/vention-storage/) to save configuration (e.g., cube locations) between restarts.
  - [x] **Testing:** Write unit tests for the backend logic or component tests for the frontend.
  - [x] **Containerization:** Run the whole stack (Backend + Frontend) with a single command (e.g., Docker Compose).
  - [x] **Demo:** Include a short video recording of your solution in action.

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

  - [x] Fork the repository and complete the work in your fork.
  - [x] Include a **README** documenting:
      - Setup and run instructions.
      - Design decisions, assumptions, and trade-offs.
  - [x] Push your changes and share the repository link.

-----

### **Questions?**

If you have any questions about the exercise, please contact [isaac.mills@vention.cc](mailto:isaac.mills@vention.cc). Happy coding\!
