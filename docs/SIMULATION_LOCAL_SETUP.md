# AeroGuard Local & WSL2 Environment Setup Runbook
## Detailed Setup Guide for Gazebo Harmonic, ROS 2 Jazzy, ArduPilot SITL, and MAVLink Dependencies

---

## 1. Environment Classification

AeroGuard's simulation architecture operates seamlessly across two primary execution modes:

1. **Local Windows Workstation (Mock Simulation Mode)**:
   - Runs FastAPI control plane, React workstation UI, and `MockSimulationEngine`.
   - Requires zero Linux dependencies; ideal for unit testing, UI development, and rapid iteration.
2. **WSL2 / Linux Native Host (Real Gazebo + SITL Integration Mode)**:
   - Runs Gazebo Harmonic 8, ROS 2 Jazzy, and ArduPilot SITL binaries.
   - Provides full physics simulation and real MAVLink UDP stream output.

---

## 2. WSL2 Ubuntu 24.04 Setup Instructions

### Step 1: Install Gazebo Harmonic 8
```bash
sudo apt update && sudo apt install -y lsb-release wget gnupg
sudo wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt update
sudo apt install -y gz-harmonic
```

### Step 2: Install ArduPilot SITL Prereqs & Repository
```bash
git clone --recursive https://github.com/ArduPilot/ardupilot.git ~/ardupilot
cd ~/ardupilot
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile
./waf configure --board sitl
./waf copter
```

### Step 3: Configure Environment Variables
Set variables in `backend/.env` or system environment:
```bash
export AEROGUARD_GAZEBO_PATH="/usr/bin/gz"
export AEROGUARD_ARDUPILOT_SITL_PATH="$HOME/ardupilot/Tools/autotest/sim_vehicle.py"
```

---

## 3. Environment Capability Diagnostic API Verification

Query the capability endpoint to confirm setup:
```bash
curl -X GET "http://localhost:8000/api/v1/simulation/capabilities"
```
Response:
```json
{
  "gazebo": { "available": true, "version": "Harmonic 8.0", "path": "/usr/bin/gz" },
  "ardupilot_sitl": { "available": true, "version": "ArduCopter 4.5.1", "path": "/home/user/ardupilot/Tools/autotest/sim_vehicle.py" },
  "mavlink": { "available": true, "version": "pymavlink" },
  "system_os": "linux"
}
```
