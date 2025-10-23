# 🧪 Fertigation Control Process Simulation (Python Task)

### **Objective**
Simulate a fertigation control cycle using Python, incorporating timing, concurrency, sensor simulation, and event logging.  
This task represents a simplified version of how fertigation logic executes in an actual field controller.

---

## **📥 Input Configuration (control_signal.json)**

```json
{
    "initial_delay": 300, 
    "flush": 120,
    "tanks": [1000, 2000, 1500],
    "duty_cycle": {
        "ec": 0.5,
        "ph": 6.5
    }
}
```

### **Description of Fields**
| Field | Type | Description |
|--------|------|-------------|
| `initial_delay` | int | Delay (in seconds) before starting the fertigation sequence. |
| `flush` | int | Duration (in seconds) for final flushing after tanks finish. |
| `tanks` | list[int] | Duration (in seconds) for each tank to run. All tank timers should run **in parallel**. |
| `duty_cycle.ec` | float | Target EC (Electrical Conductivity) value. |
| `duty_cycle.ph` | float | Target pH level for fertigation solution. |

---

## **🧩 Task Overview**

As a developer you are required to simulate the fertigation control logic based on the configuration above.  
The flow should closely follow these steps:

### **1. Initialization Phase**


- Read the configuration from `control_signal.json`.
- Wait for `initial_delay` seconds before starting any operation.
- Log event:  
  ```
  [timestamp] Initialization delay started (300s)
  [timestamp] Initialization delay completed
  ```

---

### **2. Tank Operation Phase**
- Start all tank timers **in parallel** (using `asyncio` or `threading`).
- Each tank should log its start and stop events:
  ```
  [timestamp] Tank 1 started (Duration: 1000s)
  [timestamp] Tank 1 completed
  ```
- Determine the **maximum tank duration**. Fertigation will run concurrently and end automatically when this timer completes.

---

### **3. Fertigation Process Phase (Concurrent with Tanks)**

During this phase, fertigation runs **in parallel** with tank timers and stops automatically when the tank with the maximum duration completes. EC and pH simulation continues independently throughout this period.

#### **Steps:**
1. **Apply Duty Cycle Setpoints:**  
   Use the provided `ec` and `ph` values from the duty cycle as target setpoints for fertigation.

2. **Maintain Fertigation Conditions:**  
   Continue the fertigation process **for the duration of the maximum tank timer**.

3. **Simulate Sensor Readings:**  
   Every **30 seconds**, generate a random pH value between **5.0** and **8.0** to mimic real-time sensor behavior.

4. **Evaluate pH Readings and Trigger Events:**
   - **If pH > 7.0:**  
     - Simulate an **“Acid pH Tank Started”** event.  
     - Begin tracking the active time of the acid tank.  
   - **If pH < 6.0:**  
     - Simulate a **“Base pH Tank Started”** event.  
     - Begin tracking the active time of the base tank.  
   - **If 6.0 ≤ pH ≤ 7.0:**  
     - Log a **“pH Stable”** event.  
     - If either the acid or base tank was previously running, simulate a **“Tank Stopped”** event for that tank, noting how long it was active.  
       Example: *“pH stable — Acid pH tank stopped (ran for 100 sec)”*.

5. **Log All Events:**  
   Every reading and event (start, stop, stable) must be recorded with timestamps for monitoring and debugging.

#### **Example Logs:**
```
[2025-10-16 11:05:00] Tank 1 started (Duration: 1000s)
[2025-10-16 11:05:00] Tank 2 started (Duration: 2000s)
[2025-10-16 11:05:00] Tank 3 started (Duration: 1500s)
[2025-10-16 11:05:00] Fertigation started (Concurrent with tanks)
[2025-10-16 11:05:30] pH reading: 7.2 → Acid pH Tank Started
[2025-10-16 11:06:00] pH reading: 6.8 → pH Stable — Acid pH Tank Stopped (ran for 30s)
[2025-10-16 11:06:30] pH reading: 5.9 → Base pH Tank Started
[2025-10-16 11:07:00] pH reading: 6.5 → pH Stable — Base pH Tank Stopped (ran for 30s)
[2025-10-16 11:38:20] Maximum tank duration reached — Fertigation completed
```

---

### **4. Flush Phase**
- After all tanks are done, run the **flush** timer for the specified duration.
- Log flush start and completion events:
  ```
  [timestamp] Flush started (Duration: 120s)
  [timestamp] Flush completed
  ```

---

### **5. Logging Requirements**
- Use Python’s built-in `logging` module or print statements with formatted timestamps.
- Each log should include:
  - Timestamp  
  - Event description  
  - Associated values (e.g., tank number, reading)
- Store all logs in a file named **`fertigation_log.txt`**.

---

## **🧱 Code Structure Expectations**
Organize your code in a modular manner:

```python
class FertigationController:
    def __init__(self, config_file):
        # Load configuration, initialize counters, etc.

    def init_delay(self):
        # Handle initial delay

    def run_tanks(self):
        # Run all tanks concurrently

    def control_fertigation(self):
        # Run fertigation process in parallel with tanks

    def flush(self):
        # Handle flush process

    def log_event(self, message):
        # Handle logging of all events

    def run(self):
        # Execute all phases sequentially but run fertigation concurrently with tanks
```

- Program entry point:
  ```python
  if __name__ == "__main__":
      controller = FertigationController("control_signal.json")
      controller.run()
  ```

---

### **🌱 Optional Bonus (for Extra Credit)**
Developers can extend functionality with:
- Graceful handling of interrupts (`KeyboardInterrupt`) with proper log closure.

---

### **💡 Example Command to Run**
```bash
python fertigation_controller.py
```
