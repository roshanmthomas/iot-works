"""
Fertigation Control Process Simulation (Threading Version)

This module simulates a fertigation control system that manages irrigation and fertilization
processes in agricultural applications using Python threading for concurrent operations.

Key Features:
- Threaded tank operations running in parallel
- Real-time pH monitoring and automatic adjustment
- Comprehensive event logging with timestamps
- Graceful shutdown handling
- Configuration-based operation

Author: Roshan M Thomas
Date: 23 October 2025
"""

import json
import threading
import time
import random
import logging
from datetime import datetime
import signal
import sys
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class FertigationController:
    """
    Main controller class for the fertigation process simulation using threading.
    
    This class orchestrates the entire fertigation cycle including:
    - Initial delay phase
    - Concurrent tank operations using threads
    - pH monitoring and adjustment in separate thread
    - Final flush phase
    
    Attributes:
        config (Dict): Configuration loaded from JSON file
        acid_tank_start_time (Optional[datetime]): When acid tank started (None if not running)
        base_tank_start_time (Optional[datetime]): When base tank started (None if not running)
        acid_tank_count (int): Number of times acid tank has been started
        base_tank_count (int): Number of times base tank has been started
        fertigation_running_event (threading.Event): Event to control fertigation loop
        logger (logging.Logger): Logger instance for event recording
        lock (threading.Lock): Thread synchronization lock for shared resources
        shutdown_event (threading.Event): Event to signal shutdown across threads
    """
    
    def __init__(self, config_file: str):
        """
        Initialize the fertigation controller with configuration.
        
        Args:
            config_file (str): Path to the JSON configuration file
            
        The constructor performs the following:
        1. Loads configuration from JSON file
        2. Initializes tracking variables for pH tank operations
        3. Sets up threading synchronization primitives
        4. Sets up logging system
        5. Registers signal handler for graceful shutdown
        """
        # Initialize logging system
        self.setup_logging()

        self.config = self.load_config(config_file)
        self.validate_config()
        
        # pH tank tracking variables
        self.acid_tank_start_time: Optional[datetime] = None
        self.base_tank_start_time: Optional[datetime] = None
        self.acid_tank_count = 0
        self.base_tank_count = 0      
        
        # Threading synchronization primitives
        self.lock = threading.Lock()  # Protects shared state
        self.shutdown_event = threading.Event()  # Signals shutdown to all threads
        self.fertigation_running_event = threading.Event()  # Controls fertigation loop
        
        # Setup signal handler for graceful shutdown (Ctrl+C)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file with error handling.
        
        Args:
            config_file (str): Path to the configuration file
            
        Returns:
            Dict[str, Any]: Parsed configuration dictionary
            
        Raises:
            SystemExit: If file not found or JSON is invalid
            
        The configuration should contain:
        - initial_delay: Seconds to wait before starting
        - flush: Duration of final flush phase
        - tanks: List of tank durations (run in parallel)
        - duty_cycle: Target EC and pH values
        """
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in configuration file {config_file}: {e}")
            sys.exit(1)
    
    def setup_logging(self):
        """
        Configure isolated logging system to avoid conflicts.
        """
        # Create a unique logger name to avoid conflicts
        logger_name = f"fertigation_{id(self)}"
        self.logger = logging.getLogger(logger_name)
        
        # Clear any existing handlers for this specific logger
        self.logger.handlers.clear()
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Prevent propagation to root logger
        
        # Create formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler
        file_handler = logging.FileHandler('fertigation_log_ctrl_c.txt', mode='w')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Console handler with explicit stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Add handlers to our specific logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Suppress other common loggers that might interfere
        for logger_name in ['asyncio', 'urllib3', 'requests']:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
            logging.getLogger(logger_name).propagate = False
    
    def validate_config(self):
        """
        Validate the loaded configuration for required keys and types.
        Raises:
            ValueError: If required keys are missing or invalid types
        """
        required_keys = ['initial_delay', 'flush', 'tanks', 'duty_cycle']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

        # pH reading interval (optional, default 30s)
        self.ph_interval = self.config.get('ph_interval', 30)
        if not isinstance(self.ph_interval, int) or self.ph_interval <= 0:
            raise ValueError("ph_interval must be a positive integer")
        
    def signal_handler(self, signum: int, frame):
        """
        Handle KeyboardInterrupt (Ctrl+C) gracefully in threaded environment.
        
        Args:
            signum (int): Signal number
            frame: Current stack frame
            
        This ensures proper cleanup and logging when the program is interrupted.
        Sets shutdown event to signal all threads to stop gracefully.
        """
        # self.log_event("=== Fertigation Process Interrupted by User ===")
        # self.log_event("Performing graceful shutdown...")
        
        # # Signal all threads to shutdown
        # self.shutdown_event.set()
        # self.fertigation_running_event.clear()
        
        # # Stop any running pH tanks (thread-safe)
        # with self.lock:
        #     if self.acid_tank_start_time is not None:
        #         duration = (datetime.now() - self.acid_tank_start_time).total_seconds()
        #         self.log_event(f"Acid pH Tank force stopped (was running for {int(duration)}s)")
            
        #     if self.base_tank_start_time is not None:
        #         duration = (datetime.now() - self.base_tank_start_time).total_seconds()
        #         self.log_event(f"Base pH Tank force stopped (was running for {int(duration)}s)")
        
        # self.log_event("Shutdown completed")
        # sys.exit(0)
        self.log_event("=== Fertigation Process Interrupted by User ===")
        self.log_event("Performing graceful shutdown...")
        
        # Signal all threads to shutdown
        self.shutdown_event.set()
        self.fertigation_running_event.clear()
        
        # Stop any running pH tanks (thread-safe)
        with self.lock:
            if self.acid_tank_start_time is not None:
                duration = (datetime.now() - self.acid_tank_start_time).total_seconds()
                self.log_event(f"Acid pH Tank force stopped (was running for {int(duration)}s)")
            
            if self.base_tank_start_time is not None:
                duration = (datetime.now() - self.base_tank_start_time).total_seconds()
                self.log_event(f"Base pH Tank force stopped (was running for {int(duration)}s)")
        
        self.log_event("Shutdown signalled; waiting for threads to exit...")
    
    def log_event(self, message: str):
        """
        Log events with consistent formatting (thread-safe).
        
        Args:
            message (str): The message to log
            
        All events are logged with timestamps to both file and console.
        Python's logging module handles thread safety automatically.
        """
        self.logger.info(message)
    
    def init_delay(self):
        """
        Handle the initial delay phase before starting operations.
        
        This delay allows the system to stabilize before beginning the fertigation process.
        Duration is specified in the configuration file.
        
        Uses time.sleep() which blocks the current thread but doesn't affect other threads.
        """
        delay = self.config['initial_delay']
        self.log_event(f"Initialization delay started ({delay}s)")

        # Check for shutdown during delay (every second)
        for _ in range(delay):
            if self.shutdown_event.is_set():
                return
            time.sleep(1)
        
        self.log_event("Initialization delay completed")
    
    def run_tank(self, tank_number: int, duration: int):
        """
        Run a single tank for the specified duration (thread function).
        
        Args:
            tank_number (int): Tank identifier (1, 2, 3, etc.)
            duration (int): How long the tank should run in seconds
            
        This function represents the operation of one fertilizer/nutrient tank.
        Each tank runs in its own thread, allowing parallel operation.
        
        The function checks for shutdown signals periodically to enable graceful termination.
        """
        self.log_event(f"Tank {tank_number} started (Duration: {duration}s)")
        
        # Simulate tank operation with interruptible sleep
        start_time = time.time()
        while time.time() - start_time < duration:
            if self.shutdown_event.is_set():
                self.log_event(f"Tank {tank_number} interrupted during operation")
                return
            time.sleep(1)  # Sleep in small increments to check shutdown signal
        
        self.log_event(f"Tank {tank_number} completed")
    
    def run_tanks(self):
        """
        Run all tanks concurrently using ThreadPoolExecutor.
        
        Creates separate threads for each tank so they run in parallel.
        Uses ThreadPoolExecutor for proper thread management and cleanup.
        
        This simulates real-world scenario where multiple fertilizer tanks
        can operate simultaneously with different durations.
        """
        tank_threads = []
        
        # Create thread for each tank using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(self.config['tanks'])) as executor:
            # Submit each tank as a separate thread
            for i, duration in enumerate(self.config['tanks'], 1):
                future = executor.submit(self.run_tank, i, duration)
                tank_threads.append(future)
            
            # Wait for all tank threads to complete
            for future in as_completed(tank_threads):
                try:
                    future.result()  # Get result or raise exception if any
                except Exception as e:
                    self.log_event(f"Tank thread error: {e}")
        
        if not self.shutdown_event.is_set():
            self.log_event("All tanks completed")
    
    def generate_ph_reading(self) -> float:
        """
        Simulate a pH sensor reading.
        
        Returns:
            float: Random pH value between 5.0 and 8.0
            
        In a real system, this would read from actual pH sensors.
        The random generation simulates the natural variation in pH levels
        that would occur during fertigation.
        
        This function is thread-safe as it only uses local variables.
        """
        return round(random.uniform(5.0, 8.0), 1)
    
    def handle_ph_reading(self, ph_value: float):
        """
        Process pH reading and manage acid/base tank operations (thread-safe).
        
        Args:
            ph_value (float): Current pH reading from sensor
            
        pH Management Logic:
        - pH > 7.0: Too alkaline → Start acid tank to lower pH
        - pH < 6.0: Too acidic → Start base tank to raise pH  
        - 6.0 ≤ pH ≤ 7.0: Optimal range → Stop any running tanks
        
        The system tracks when tanks start/stop and counts total activations.
        Uses threading.Lock to ensure thread-safe access to shared state.
        """
        current_time = datetime.now()
        
        # Use lock to ensure thread-safe access to shared variables
        with self.lock:
            if ph_value > 7.0:
                # pH too high (alkaline) - need acid to lower it
                
                # Stop base tank if it's running (we don't need it anymore)
                if self.base_tank_start_time is not None:
                    duration = (current_time - self.base_tank_start_time).total_seconds()
                    self.log_event(f"pH reading: {ph_value:.1f} -> pH Stable - Base pH Tank Stopped (ran for {int(duration)}s)")
                    self.base_tank_start_time = None
                
                # Start acid tank if not already running
                if self.acid_tank_start_time is None:
                    self.log_event(f"pH reading: {ph_value:.1f} -> Acid pH Tank Started")
                    self.acid_tank_start_time = current_time
                    self.acid_tank_count += 1
                else:
                    # Acid tank already running, just log the reading
                    self.log_event(f"pH reading: {ph_value:.1f} -> stable")
            
            elif ph_value < 6.0:
                # pH too low (acidic) - need base to raise it
                
                # Stop acid tank if it's running
                if self.acid_tank_start_time is not None:
                    duration = (current_time - self.acid_tank_start_time).total_seconds()
                    self.log_event(f"pH reading: {ph_value:.1f} -> pH Stable - Acid pH Tank Stopped (ran for {int(duration)}s)")
                    self.acid_tank_start_time = None
                
                # Start base tank if not already running
                if self.base_tank_start_time is None:
                    self.log_event(f"pH reading: {ph_value:.1f} -> Base pH Tank Started")
                    self.base_tank_start_time = current_time
                    self.base_tank_count += 1
                else:
                    # Base tank already running, just log the reading
                    self.log_event(f"pH reading: {ph_value:.1f} -> stable")
            
            else:
                # pH in optimal range (6.0 - 7.0) - stop any running tanks
                
                if self.acid_tank_start_time is not None:
                    # Stop acid tank
                    duration = (current_time - self.acid_tank_start_time).total_seconds()
                    self.log_event(f"pH reading: {ph_value:.1f} -> pH Stable - Acid pH Tank Stopped (ran for {int(duration)}s)")
                    self.acid_tank_start_time = None
                    
                elif self.base_tank_start_time is not None:
                    # Stop base tank
                    duration = (current_time - self.base_tank_start_time).total_seconds()
                    self.log_event(f"pH reading: {ph_value:.1f} -> pH Stable - Base pH Tank Stopped (ran for {int(duration)}s)")
                    self.base_tank_start_time = None
                    
                else:
                    # No tanks running, pH is stable
                    self.log_event(f"pH reading: {ph_value:.1f} -> pH Stable")
    
    def control_fertigation(self):
        """
        Control the fertigation process with continuous pH monitoring (thread function).
        
        This function runs in its own thread concurrently with tank operations and:
        1. Monitors pH levels every specified pH reading interval seconds
        2. Automatically adjusts pH using acid/base tanks
        3. Runs for the duration of the longest tank
        4. Stops when maximum tank duration is reached or shutdown is signaled
        
        The fertigation process simulates real-time control where pH
        must be continuously monitored and adjusted during irrigation.
        """
        # Calculate how long fertility should run (duration of longest tank)
        max_duration = max(self.config['tanks'])
        
        # Log fertigation startup with target values
        ec_target = self.config['duty_cycle']['ec']
        ph_target = self.config['duty_cycle']['ph']
        self.log_event(f"Fertigation started (Concurrent with tanks, Target EC: {ec_target}, Target pH: {ph_target})")
        
        # Start fertigation control loop
        self.fertigation_running_event.set()
        start_time = time.time()
        
        # Main fertigation control loop - runs until longest tank completes or shutdown
        while self.fertigation_running_event.is_set() and not self.shutdown_event.is_set():
            # Generate simulated pH reading
            ph_reading = self.generate_ph_reading()
            
            # Process the reading and adjust pH tanks accordingly
            self.handle_ph_reading(ph_reading)
            
            # Check if we've reached the maximum tank duration
            elapsed = time.time() - start_time
            if elapsed >= max_duration:
                self.fertigation_running_event.clear()
                break

            # Wait for the specified pH reading interval (with shutdown check)
            for _ in range(self.ph_interval):
                if self.shutdown_event.is_set() or not self.fertigation_running_event.is_set():
                    break
                time.sleep(1)
        
        # Fertigation period ended - stop any running pH tanks
        if not self.shutdown_event.is_set():
            self.stop_running_ph_tanks("Fertigation completed")
            self.log_event("Maximum tank duration reached - Fertigation completed")
    
    def stop_running_ph_tanks(self, reason: str):
        """
        Stop any currently running pH tanks and log the duration (thread-safe).
        
        Args:
            reason (str): Reason for stopping (e.g., "Fertigation completed")
            
        This is called when fertigation ends to ensure all pH tanks are stopped
        and their run times are properly logged.
        
        Uses threading.Lock to ensure thread-safe access to shared state.
        """
        current_time = datetime.now()
        
        with self.lock:
            if self.acid_tank_start_time is not None:
                duration = (current_time - self.acid_tank_start_time).total_seconds()
                self.log_event(f"{reason} - Acid pH Tank Stopped (ran for {int(duration)}s)")
                self.acid_tank_start_time = None
                
            if self.base_tank_start_time is not None:
                duration = (current_time - self.base_tank_start_time).total_seconds()
                self.log_event(f"{reason} - Base pH Tank Stopped (ran for {int(duration)}s)")
                self.base_tank_start_time = None
    
    def flush(self):
        """
        Handle the final flush phase after all tanks complete.
        
        The flush phase cleans the irrigation system by running clean water
        through all lines to remove any remaining fertilizer solution.
        Duration is specified in the configuration file.
        
        Uses interruptible sleep to respond to shutdown signals.
        """
        flush_duration = self.config['flush']
        self.log_event(f"Flush started (Duration: {flush_duration}s)")
        
        # Simulate flush operation with interruptible sleep
        for _ in range(flush_duration):
            if self.shutdown_event.is_set():
                self.log_event("Flush interrupted")
                return
            time.sleep(1)
        
        self.log_event("Flush completed")
    
    def generate_summary(self) -> str:
        """
        Generate a summary report of the fertigation process (thread-safe).
        
        Returns:
            str: Formatted summary string
            
        The summary includes:
        - Number of times acid tank was activated
        - Number of times base tank was activated  
        - Total duration (based on longest tank)
        
        Uses lock to ensure thread-safe access to counters.
        """
        with self.lock:
            total_duration = max(self.config['tanks'])
            
            summary = (f"Summary: Acid pH Tank Started = {self.acid_tank_count} time(s), "
                      f"Base pH Tank Started = {self.base_tank_count} time(s), "
                      f"Total Duration = {total_duration}s")
            
            return summary
    
    def run(self):
        """
        Execute the complete fertigation control sequence using threading.
        
        This is the main orchestration method that coordinates all phases:
        
        Phase 1: Initialization delay (sequential)
        Phase 2 & 3: Tank operations + Fertigation control (concurrent threads)
        Phase 4: Flush operation (sequential)
        Phase 5: Summary report
        
        The method uses threading to run tanks and fertigation concurrently,
        which simulates real-world operation where irrigation and pH control
        happen simultaneously.
        """
        try:
            # Log process start
            self.log_event("=== Fertigation Control Started ===")
            self.log_event(f"Configuration loaded from control_signal.json")
            
            # Phase 1: Initialization delay (wait before starting anything)
            self.init_delay()
            
            if self.shutdown_event.is_set():
                self.log_event("Shutdown requested before operations started")
                return
            
            # Phase 2 & 3: Run tanks and fertigation concurrently using threads
            # This simulates real operation where irrigation tanks run while
            # pH is continuously monitored and adjusted
            self.log_event("Starting concurrent operations: Tanks + Fertigation")
            
            # Create threads for tank operations and fertigation control
            tank_thread = threading.Thread(target=self.run_tanks, name="TankThread", daemon=True)
            fertigation_thread = threading.Thread(target=self.control_fertigation, name="FertigationThread", daemon=True)
            
            # Start both threads
            tank_thread.start()
            fertigation_thread.start()
            
            # Wait for both threads to complete
            while tank_thread.is_alive() or fertigation_thread.is_alive():
                tank_thread.join(timeout=0.5)
                fertigation_thread.join(timeout=0.5)
            
            if self.shutdown_event.is_set():
                self.log_event("Shutdown requested - skipping flush/summary")
                return
            
            # Phase 4: Flush (run after everything else completes)
            self.flush()
            
            if self.shutdown_event.is_set():
                self.log_event("Shutdown requested during flush")
                return
            
            # Phase 5: Generate final summary and log completion
            self.log_event("=== Fertigation Process Ended ===")
            summary = self.generate_summary()
            self.log_event(summary)
            
            self.log_event("Process completed successfully!")
            
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            self.signal_handler(signal.SIGINT, None)
            sys.exit(0)
        except Exception as e:
            # Handle any unexpected errors
            self.log_event(f"Unexpected error occurred: {e}")
            raise


# Program entry point
if __name__ == "__main__":
    """
    Main execution block for threading version.
    
    This creates a FertigationController instance and runs the complete process.
    The program expects a 'control_signal.json' file in the same directory.
    
    Usage:
        python fertigation_controller_threading.py
        
    The program will:
    1. Load configuration from control_signal.json
    2. Execute the complete fertigation sequence using threads
    3. Log all events to fertigation_log.txt and console
    4. Handle interrupts gracefully with proper thread cleanup
    """
    print("Fertigation Control System Starting...")
    print("Logs will be written to 'fertigation_log_ctrl_c.txt'")
    print("Press Ctrl+C to stop the process gracefully")
    print("-" * 50)
    
    # Create and run the controller
    controller = FertigationController("control_signal.json")
    
    # Run the threading-based process
    controller.run()