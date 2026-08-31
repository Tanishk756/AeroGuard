# AeroGuard Local & WSL2 Environment Setup Runbook
## Detailed Setup Guide for Gazebo Harmonic 8.15.0, ArduPilot SITL 4.6.0, and MAVLink Dependencies

---

## 1. Environment Classification

AeroGuard's simulation architecture operates seamlessly across two primary execution modes:

1. **Local Windows Workstation (Mock Simulation Mode)**:
   - Runs FastAPI control plane, React workstation UI, and `MockSimulationEngine`.
   - Requires zero Linux dependencies; ideal for unit testing, UI development, and rapid iteration.
2. **WSL2 Linux Host (Real Gazebo + SITL Integration Mode - LIVE VERIFIED)**:
   - Runs Gazebo Harmonic 8.15.0 (`/usr/bin/gz`) and ArduCopter SITL 4.6.0 (`/home/tanishk/src/ardupilot/build/sitl/bin/arducopter`).
   - Provides real physics simulation and live MAVLink UDP packet streaming (`udpin:127.0.0.1:14550`).

---

## 2. Verified WSL2 Ubuntu 22.04 Setup Instructions

### Step 1: Install Gazebo Harmonic 8.15.0
```bash
sudo apt update && sudo apt install -y lsb-release wget gnupg
sudo wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt update
sudo apt install -y gz-harmonic
```

### Step 2: Build ArduPilot SITL (ArduCopter)
```bash
mkdir -p ~/src && cd ~/src
git clone --depth 1 https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git submodule update --init --recursive
./waf configure --board sitl
./waf copter
```
The compiled binary will be produced at `~/src/ardupilot/build/sitl/bin/arducopter`.

---

## 3. Environment Capability Diagnostic API Verification

Query the capability endpoint to confirm setup:
```bash
curl -X GET "http://localhost:8000/api/v1/simulation/capabilities"
```
Response:
```json
{
  "gazebo": {
    "available": true,
    "version": "Harmonic 8.15.0",
    "reason": null,
    "path": "WSL:/usr/bin/gz"
  },
  "ardupilot_sitl": {
    "available": true,
    "version": "ArduCopter 4.6.0-dev",
    "reason": null,
    "path": "WSL:/home/tanishk/src/ardupilot/build/sitl/bin/arducopter"
  },
  "mavlink": {
    "available": true,
    "version": "2.4.49"
  },
  "system_os": "win32"
}
```
