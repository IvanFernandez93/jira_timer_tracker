"""
Optimized Application Startup Manager
Handles application initialization with performance monitoring and lazy loading.
"""

import time
import logging
import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QApplication, QSplashScreen, QProgressBar
from PyQt6.QtGui import QPixmap
import concurrent.futures

logger = logging.getLogger(__name__)

@dataclass
class StartupTask:
    """Represents a startup initialization task."""
    name: str
    function: Callable
    priority: int = 1  # 1 = critical, 2 = important, 3 = optional
    depends_on: List[str] = None
    timeout: float = 30.0
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []

class StartupWorker(QThread):
    """Background worker for startup tasks."""
    
    task_completed = pyqtSignal(str, bool, str)  # name, success, message
    progress_updated = pyqtSignal(int, str)  # percentage, current_task
    
    def __init__(self, tasks: List[StartupTask]):
        super().__init__()
        self.tasks = tasks
        self.completed_tasks = set()
        self.failed_tasks = set()
        
    def run(self):
        """Execute startup tasks with dependency resolution."""
        total_tasks = len(self.tasks)
        completed = 0
        
        # Sort tasks by priority
        priority_tasks = sorted(self.tasks, key=lambda t: t.priority)
        
        for task in priority_tasks:
            if self._can_execute_task(task):
                success, message = self._execute_task(task)
                
                if success:
                    self.completed_tasks.add(task.name)
                else:
                    self.failed_tasks.add(task.name)
                    if task.priority == 1:  # Critical task failed
                        logger.error(f"Critical task failed: {task.name} - {message}")
                        break
                
                completed += 1
                progress = int((completed / total_tasks) * 100)
                self.progress_updated.emit(progress, task.name)
                self.task_completed.emit(task.name, success, message)
    
    def _can_execute_task(self, task: StartupTask) -> bool:
        """Check if task dependencies are satisfied."""
        return all(dep in self.completed_tasks for dep in task.depends_on)
    
    def _execute_task(self, task: StartupTask) -> tuple[bool, str]:
        """Execute a single startup task with timeout."""
        try:
            start_time = time.time()
            
            # Execute with timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(task.function)
                try:
                    result = future.result(timeout=task.timeout)
                    execution_time = time.time() - start_time
                    
                    logger.info(f"Task '{task.name}' completed in {execution_time:.2f}s")
                    return True, f"Completato in {execution_time:.2f}s"
                    
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Task '{task.name}' timed out after {task.timeout}s")
                    return False, f"Timeout dopo {task.timeout}s"
                    
        except Exception as e:
            logger.error(f"Task '{task.name}' failed: {e}")
            return False, str(e)

class AppStartupManager(QObject):
    """
    Manages application startup with performance optimizations and user feedback.
    Provides splash screen, progress tracking, and lazy initialization.
    """
    
    startup_completed = pyqtSignal(bool, dict)  # success, performance_stats
    
    def __init__(self):
        super().__init__()
        self.splash_screen = None
        self.startup_tasks = []
        self.performance_stats = {}
        self.startup_worker = None
        
    def add_startup_task(self, name: str, function: Callable, priority: int = 2,
                        depends_on: List[str] = None, timeout: float = 30.0):
        """Add a task to the startup sequence."""
        task = StartupTask(
            name=name,
            function=function,
            priority=priority,
            depends_on=depends_on or [],
            timeout=timeout
        )
        self.startup_tasks.append(task)
        
    def create_splash_screen(self, image_path: Optional[str] = None) -> QSplashScreen:
        """Create and configure splash screen."""
        try:
            if image_path:
                pixmap = QPixmap(image_path)
            else:
                # Create a simple colored splash screen
                pixmap = QPixmap(400, 300)
                pixmap.fill()
            
            self.splash_screen = QSplashScreen(pixmap)
            self.splash_screen.show()
            
            return self.splash_screen
            
        except Exception as e:
            logger.warning(f"Could not create splash screen: {e}")
            return None
    
    def start_initialization(self, show_splash: bool = True, splash_image: Optional[str] = None):
        """Start the application initialization process."""
        start_time = time.time()
        
        if show_splash:
            self.create_splash_screen(splash_image)
        
        # Create and start worker thread
        self.startup_worker = StartupWorker(self.startup_tasks)
        self.startup_worker.task_completed.connect(self._on_task_completed)
        self.startup_worker.progress_updated.connect(self._on_progress_updated)
        self.startup_worker.finished.connect(
            lambda: self._on_startup_finished(start_time)
        )
        
        self.startup_worker.start()
    
    def _on_task_completed(self, task_name: str, success: bool, message: str):
        """Handle individual task completion."""
        if self.splash_screen:
            status = "✓" if success else "✗"
            self.splash_screen.showMessage(
                f"{status} {task_name}: {message}",
                alignment=1  # Qt.AlignLeft
            )
    
    def _on_progress_updated(self, percentage: int, current_task: str):
        """Update progress display."""
        if self.splash_screen:
            self.splash_screen.showMessage(
                f"Inizializzazione: {current_task} ({percentage}%)",
                alignment=1  # Qt.AlignLeft
            )
    
    def _on_startup_finished(self, start_time: float):
        """Handle startup completion."""
        total_time = time.time() - start_time
        
        # Collect performance statistics
        self.performance_stats = {
            'total_time': total_time,
            'completed_tasks': len(self.startup_worker.completed_tasks),
            'failed_tasks': len(self.startup_worker.failed_tasks),
            'success_rate': len(self.startup_worker.completed_tasks) / len(self.startup_tasks) * 100
        }
        
        # Close splash screen
        if self.splash_screen:
            QTimer.singleShot(1000, self.splash_screen.close)  # Show result for 1s
        
        # Determine overall success
        critical_failed = any(
            task.name in self.startup_worker.failed_tasks and task.priority == 1
            for task in self.startup_tasks
        )
        
        success = not critical_failed
        
        logger.info(f"Startup completed in {total_time:.2f}s - Success: {success}")
        logger.info(f"Performance stats: {self.performance_stats}")
        
        self.startup_completed.emit(success, self.performance_stats)

class LazyInitializer:
    """
    Lazy initialization helper for expensive resources.
    Implements singleton pattern with thread-safe initialization.
    """
    
    def __init__(self):
        self._instances = {}
        self._locks = {}
    
    def get_or_create(self, key: str, factory: Callable, *args, **kwargs) -> Any:
        """Get existing instance or create new one using factory."""
        if key not in self._instances:
            # Thread-safe initialization
            if key not in self._locks:
                import threading
                self._locks[key] = threading.Lock()
            
            with self._locks[key]:
                if key not in self._instances:  # Double-check
                    try:
                        start_time = time.time()
                        instance = factory(*args, **kwargs)
                        creation_time = time.time() - start_time
                        
                        self._instances[key] = instance
                        logger.debug(f"Lazy-created '{key}' in {creation_time:.3f}s")
                        
                    except Exception as e:
                        logger.error(f"Failed to create '{key}': {e}")
                        raise
        
        return self._instances[key]
    
    def preload(self, key: str, factory: Callable, *args, **kwargs):
        """Preload an instance in background."""
        def _preload():
            self.get_or_create(key, factory, *args, **kwargs)
        
        import threading
        thread = threading.Thread(target=_preload, daemon=True)
        thread.start()

# Global lazy initializer instance
lazy_init = LazyInitializer()

# Common startup task implementations
def init_logging():
    """Initialize application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    logger.info("Logging initialized")

def init_database_connection(db_service):
    """Initialize database connection."""
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        logger.info("Database connection verified")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def init_git_repository(git_service):
    """Initialize git repository for notes."""
    try:
        git_service.init_repository()
        logger.info("Git repository initialized")
        return True
    except Exception as e:
        logger.error(f"Git initialization failed: {e}")
        raise

def verify_jira_connection(jira_service):
    """Verify JIRA connection (non-critical)."""
    try:
        # This would be a lightweight check
        return jira_service.test_connection()
    except Exception as e:
        logger.warning(f"JIRA connection check failed: {e}")
        return False