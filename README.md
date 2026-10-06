# ADRN: Advanced Distributed Robotics Network

## Architecture Overview
The system follows a separated Control Plane / Data Plane architecture, similar to industrial orchestration systems like Kubernetes or ROS2 with a central manager.

### 1. Client (Architect UI)
- **Role**: The visual interface for users to build node graphs, view logs, and manage the network.
- **Tech**: React + React Flow (Web Application).
- **Access**: Connects to the Orchestrator. Multiple clients can connect to one Orchestrator.

### 2. Orchestrator (Control Plane / Server)
- **Role**: The central management server. Handles user authentication, RBAC (Role-Based Access Control), deployment via SSH, and stores network logs/history.
- **Security**: Can be run locally for home use or on a dedicated server for enterprise. Configs and project files can be AES-encrypted at rest.
- **Tech**: Python (FastAPI), SQLite/PostgreSQL, Paramiko (SSH).

### 3. Worker Nodes (Data Plane)
- **Role**: Physical machines (Raspberry Pi, PCs) executing the Python node logic.
- **Communication**: 
  - To Orchestrator: Fetch configs, send logs.
  - To other Nodes: Direct Peer-to-Peer (P2P) communication via **ZeroMQ** for passing data (images, matrices, etc.) to avoid bottlenecks.
- **Tech**: Python, ZeroMQ, UDP Broadcasts (Discovery).
