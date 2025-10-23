# 🌱 Fertigation Control System

A Python-based fertigation control system simulation that manages irrigation and fertilization processes in agricultural applications using threading for concurrent operations.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Code Documentation](#code-documentation)
- [Contributing](#contributing)
- [License](#license)

## 🔍 Overview

This fertigation control system simulates real-world agricultural irrigation and fertilization processes. It manages multiple fertilizer tanks running in parallel while continuously monitoring and adjusting pH levels through automated acid/base dosing systems.

The system is designed to mimic actual field controllers used in precision agriculture, providing:
- **Concurrent Operations**: Multiple fertilizer tanks operate simultaneously
- **Real-time pH Control**: Automated acid/base adjustments based on sensor readings
- **Comprehensive Logging**: Detailed event tracking with timestamps
- **Graceful Shutdown**: Safe interruption handling with proper cleanup

## ✨ Features

### Core Functionality
- 🔄 **Parallel Tank Operations**: Multiple fertilizer tanks run concurrently using Python threading
- 🧪 **Automated pH Management**: Real-time pH monitoring with automatic acid/base corrections
- ⏱️ **Configurable Timing**: Customizable delays, tank durations, and flush cycles
- 📊 **Event Logging**: Comprehensive logging to both file and console
- 🛡️ **Thread Safety**: Proper synchronization for concurrent operations
- 🔌 **Graceful Shutdown**: Clean exit handling with resource cleanup

### Advanced Features
- 📈 **Sensor Simulation**: Realistic pH sensor reading generation
- 🎯 **Target-based Control**: EC and pH setpoint management
- 📝 **Summary Reports**: Process statistics and tank activation counts
- 🚨 **Error Handling**: Robust configuration and runtime error management

## 🚀 Installation

### Prerequisites
- Python 3.7 or higher
- No external dependencies required (uses only Python standard library)

### Setup
1. Clone or download the project files:
```bash
git clone <repository-url>
cd iot-works
```

2. Ensure you have the required files:
   - [`fertigation_controller.py`](fertigation_controller.py) - Main controller module
   - [`control_signal.json`](control_signal.json) - Configuration file
   - [`test/test_fertigation_controller.py`](test/test_fertigation_controller.py) - Test suite

## ⚙️ Configuration

The system uses a JSON configuration file ([`control_signal.json`](control_signal.json)) to define operational parameters:

```json
{
    "initial_delay": 5,
    "flush": 10,
    "tanks": [30, 45, 60],
    "duty_cycle": {
        "ec": 2.5,
        "ph": 6.5
    },
    "ph_interval": 15
}
```

### Configuration Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `initial_delay` | `int` | Seconds to wait before starting operations |
| `flush` | `int` | Duration (seconds) for final system flush |
| `tanks` | `list[int]` | Duration (seconds) for each fertilizer tank |
| `duty_cycle.ec` | `float` | Target EC (Electrical Conductivity) value |
| `duty_cycle.ph` | `float` | Target pH level (6.0-7.0 optimal range) |
| `ph_interval` | `int` | Seconds between pH readings (optional, default 30) |


## 🎮 Usage

### Basic Operation
```bash
python fertigation_controller.py
```

The system will:
1. Load configuration from [`control_signal.json`](control_signal.json)
2. Execute initialization delay
3. Start all tanks and pH monitoring concurrently
4. Run flush cycle after tanks complete
5. Generate summary report

### Output
- **Console**: Real-time event logging with timestamps
- **File**: Complete log saved to `fertigation_log.txt`

### Example Output
```
[2025-10-16 11:05:00] === Fertigation Control Started ===
[2025-10-16 11:05:00] Configuration loaded from control_signal.json
[2025-10-16 11:05:00] Initialization delay started (5s)
[2025-10-16 11:05:05] Initialization delay completed
[2025-10-16 11:05:05] Starting concurrent operations: Tanks + Fertigation
[2025-10-16 11:05:05] Tank 1 started (Duration: 100s)
[2025-10-16 11:05:05] Tank 2 started (Duration: 200s)
[2025-10-16 11:05:05] Tank 3 started (Duration: 150s)
[2025-10-16 11:05:05] Fertigation started (Concurrent with tanks, Target EC: 0.8, Target pH: 0.7)
[2025-10-16 11:05:35] pH reading: 7.2 → Acid pH Tank Started
[2025-10-16 11:06:05] pH reading: 6.8 → pH Stable - Acid pH Tank Stopped (ran for 30s)
```

### Graceful Shutdown
Press `Ctrl+C` to safely stop the system at any time. The controller will:
- Stop all running operations
- Log final tank states and durations
- Clean up resources
- Save complete log file

## 🧪 Testing

The project includes a comprehensive test suite with 18 test cases covering:

### Test Categories
- **Initialization Testing**: Delay handling, configuration loading
- **pH Management**: Acid/base dosing calculations and timing
- **Concurrency Testing**: Thread safety and concurrent operations
- **Error Handling**: Invalid configurations and edge cases
- **Advanced Features**: Stress testing and concurrent safety

### Running Tests
```bash
# Run all tests with verbose output
pytest .\tests\test_fertigation_controller.py -v
```

### Test Coverage
The test suite includes:
- ✅ 13 core functionality tests
- ✅ 3 configuration loading tests  
- ✅ 2 advanced feature tests
- ✅ Thread safety validation
- ✅ Error condition handling
- ✅ Edge case coverage

## 📁 Project Structure

```
fertigation-control-system/
├── fertigation_controller.py          # Main controller module
├── control_signal.json               # Configuration file
├── Task.md                          # Project requirements
├── README.md                        # This file
├── tests/
│   └── test_fertigation_controller.py # Test suite
```

## 📖 Code Documentation

### FertigationController Class

The main controller class that orchestrates the fertigation process.

#### Key Methods

##### `__init__(config_file: str)`
Initialize controller with configuration file.

##### `run()`
Execute the complete fertigation sequence:
1. Initialization delay
2. Concurrent tank operations + pH monitoring
3. System flush
4. Summary generation

##### `init_delay()`
Handle initialization delay phase with shutdown responsiveness.

##### `run_tanks()`
Execute all fertilizer tanks concurrently using ThreadPoolExecutor.

##### `control_fertigation()`
Run pH monitoring and adjustment in parallel with tanks.

##### `handle_ph_reading(ph_value: float)`
Process pH readings and manage acid/base tank operations:
- pH > 7.0: Start acid tank to lower pH
- pH < 6.0: Start base tank to raise pH
- 6.0 ≤ pH ≤ 7.0: Optimal range, no adjustment needed

##### `generate_ph_reading() -> float`
Simulate pH sensor reading (5.0 - 8.0 range).

##### `flush()`
Execute final system flush phase.

##### `log_event(message: str)`
Thread-safe event logging with timestamps.

### Thread Safety

The system uses several synchronization mechanisms:
- `threading.Lock()`: Protects shared state variables
- `threading.Event()`: Coordinates shutdown across threads
- `ThreadPoolExecutor`: Manages tank operation threads
- `logging` module: Thread-safe event recording

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Ensure all tests pass
6. Submit a pull request

### Coding Standards
- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include type hints where appropriate
- Maintain thread safety for concurrent operations
- Add tests for new functionality

### Testing Requirements
- All new features must include tests
- Maintain minimum 90% test coverage
- Test both success and failure scenarios
- Verify thread safety for concurrent features

## 📄 License

This project is provided as-is for educational and development purposes. See the individual files for specific licensing information.

---

## 🔗 Quick Links

- [Main Controller](fertigation_controller.py)
- [Configuration File](control_signal.json) 
- [Test Suite](test/test_fertigation_controller.py)
- [Project Requirements](Task.md)

For questions or issues, please review the test suite and documentation, or create an issue in the project repository.