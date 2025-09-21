"""
Directory Manager - Shared working directory state across the application
"""
import os

class DirectoryManager:
    """Singleton class to manage the current working directory across the application"""
    _instance = None
    _current_directory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DirectoryManager, cls).__new__(cls)
            cls._current_directory = os.getcwd()
        return cls._instance
    
    @property
    def current_directory(self) -> str:
        """Get the current working directory"""
        return self._current_directory
    
    @current_directory.setter
    def current_directory(self, path: str):
        """Set the current working directory"""
        if os.path.isdir(path):
            self._current_directory = os.path.abspath(path)
        else:
            raise ValueError(f"Directory does not exist: {path}")
    
    def change_directory(self, path: str) -> bool:
        """Change to a new directory, return True if successful"""
        try:
            if os.path.isabs(path):
                target_path = path
            else:
                target_path = os.path.join(self._current_directory, path)
            
            target_path = os.path.normpath(target_path)
            
            if os.path.isdir(target_path):
                self._current_directory = target_path
                return True
            else:
                return False
        except Exception:
            return False
    
    def get_absolute_path(self, relative_path: str = ".") -> str:
        """Get absolute path relative to current directory"""
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.abspath(os.path.join(self._current_directory, relative_path))

# Global instance
directory_manager = DirectoryManager()
