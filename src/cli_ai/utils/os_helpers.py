import platform
import distro

def get_os_info() -> str:
    """Detects the operating system and returns a formatted string."""
    system = platform.system()

    if system=="Linux":
        try:
            # Use the distro module for detailed Linux info
            os_name = distro.name(pretty=True)
            os_id = distro.id()
            if os_id.lower() == 'openeuler' or 'hce':
                return f"The current operating system is openEuler. The correct package manager is dnf. All package installation commands should use 'sudo dnf install <package_name>'. All update commands should use 'sudo dnf update'."
            else:
                return f"The current operating system is {os_name}. Assume apt-get is the package manager unless instructed otherwise."
        except Exception:
            # Fallback if distro module fails
            return "The current operating system is Linux. The default package manager is unknown. Prioritize system-specific commands."
    elif system == "Windows":
        return "The current operating system is Windows. Assume the package manager is winget or Chocolatey."
    elif system == "Darwin":
        return "The current operating system is macOS. The package manager is Homebrew."
    else:
        return f"The current operating system is {system}. No specific package manager is known."