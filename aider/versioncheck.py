import sys
import packaging.version
import requests
import aider


def fetch_latest_version(package_name):
    """Fetch the latest version of the specified package from PyPI."""
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()["info"]["version"]
    except requests.RequestException as err:
        raise RuntimeError(f"Error fetching version from PyPI: {err}")


def parse_version(version):
    """Parse a version string into a Version object for comparison."""
    try:
        return packaging.version.parse(version)
    except packaging.version.InvalidVersion as err:
        raise ValueError(f"Invalid version string: {version}") from err


def is_update_available(latest_version, current_version):
    """Check if an update is available by comparing versions."""
    return parse_version(latest_version) > parse_version(current_version)


def print_update_instructions(latest_version, print_cmd):
    """Print instructions for upgrading the package if a new version is available."""
    print_cmd(f"Newer version v{latest_version} is available. To upgrade, run:")
    py = sys.executable
    upgrade_command = "pipx upgrade aider-chat" if "pipx" in py else f"{py} -m pip install --upgrade aider-chat"
    print_cmd(upgrade_command)


def check_for_updates(package_name, current_version, print_cmd):
    """Check for the latest version of the package and notify if an update is available."""
    try:
        latest_version = fetch_latest_version(package_name)
        if is_update_available(latest_version, current_version):
            print_update_instructions(latest_version, print_cmd)
            return True
        return False
    except (RuntimeError, ValueError) as err:
        print_cmd(err)
        return False


def check_version(print_cmd):
    """Check the current version of the package and see if an update is available."""
    package_name = "aider-chat"
    current_version = aider.__version__
    return check_for_updates(package_name, current_version, print_cmd)


if __name__ == "__main__":
    check_version(print)
