"""
Component Sync Service for Tier 0 (Yellow Hub) deployments.
Implements rsync-based component synchronization to standalone HA instances.
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID

from services.git_service import GitService

logger = logging.getLogger(__name__)


class ComponentSyncService:
    """Manages component synchronization to Tier 0 Yellow hubs via rsync."""

    def __init__(self, git_service: Optional[GitService] = None):
        """Initialize ComponentSyncService."""
        self.git_service = git_service or GitService()
        self.ssh_key_path = os.getenv("TIER0_SSH_KEY_PATH", "/app/config/tier0_ssh_key")
        self.ssh_user = os.getenv("TIER0_SSH_USER", "root")

    def sync_components_to_hub(
        self,
        hub_host: str,
        component_names: Optional[List[str]] = None,
        addon_names: Optional[List[str]] = None,
        custom_components_path: str = "/config/custom_components",
        addons_path: str = "/addons",
        restart_ha: bool = True,
    ) -> Dict:
        """
        Sync components and add-ons to a Tier 0 Yellow hub.

        Args:
            hub_host: SSH hostname or IP of the Yellow hub
            component_names: List of component names to sync (None = all)
            addon_names: List of addon names to sync (None = none)
            custom_components_path: Remote path for custom components
            addons_path: Remote path for add-ons
            restart_ha: Whether to restart Home Assistant after sync

        Returns:
            Dict with sync results and logs
        """
        results = {
            "hub_host": hub_host,
            "status": "success",
            "components_synced": [],
            "addons_synced": [],
            "errors": [],
            "logs": [],
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }

        logger.info(f"Starting component sync to {hub_host}")
        results["logs"].append(f"Starting sync to {hub_host}")

        # Sync components
        if component_names is None:
            # Get all available components
            try:
                all_components = self.git_service.list_components()
                component_names = [c["name"] for c in all_components]
                logger.info(f"Syncing all {len(component_names)} components")
                results["logs"].append(f"Syncing all {len(component_names)} components")
            except Exception as e:
                logger.error(f"Failed to list components: {e}")
                results["errors"].append(f"Failed to list components: {str(e)}")
                results["status"] = "failed"
                return results

        # Sync each component
        for component_name in component_names:
            try:
                component_path = self.git_service.get_component_path(component_name)
                if not component_path:
                    error_msg = f"Component not found: {component_name}"
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)
                    continue

                # Execute rsync with aggressive sync flags
                sync_result = self._rsync_component(
                    component_path=component_path,
                    component_name=component_name,
                    hub_host=hub_host,
                    remote_path=custom_components_path,
                )

                if sync_result["success"]:
                    results["components_synced"].append(component_name)
                    results["logs"].append(f"Synced component: {component_name}")
                    logger.info(f"Successfully synced component: {component_name}")
                else:
                    results["errors"].append(f"Failed to sync {component_name}: {sync_result['error']}")
                    logger.error(f"Failed to sync component {component_name}: {sync_result['error']}")

            except Exception as e:
                error_msg = f"Error syncing component {component_name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        # Sync add-ons if specified
        if addon_names:
            logger.info(f"Syncing {len(addon_names)} add-ons")
            results["logs"].append(f"Syncing {len(addon_names)} add-ons")

            for addon_name in addon_names:
                try:
                    addon_path = self.git_service.get_addon_path(addon_name)
                    if not addon_path:
                        error_msg = f"Add-on not found: {addon_name}"
                        logger.warning(error_msg)
                        results["errors"].append(error_msg)
                        continue

                    # Execute rsync for add-on
                    sync_result = self._rsync_addon(
                        addon_path=addon_path,
                        addon_name=addon_name,
                        hub_host=hub_host,
                        remote_path=addons_path,
                    )

                    if sync_result["success"]:
                        results["addons_synced"].append(addon_name)
                        results["logs"].append(f"Synced add-on: {addon_name}")
                        logger.info(f"Successfully synced add-on: {addon_name}")
                    else:
                        results["errors"].append(f"Failed to sync add-on {addon_name}: {sync_result['error']}")
                        logger.error(f"Failed to sync add-on {addon_name}: {sync_result['error']}")

                except Exception as e:
                    error_msg = f"Error syncing add-on {addon_name}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

        # Restart Home Assistant if requested and sync was successful
        if restart_ha and (results["components_synced"] or results["addons_synced"]):
            logger.info(f"Restarting Home Assistant on {hub_host}")
            results["logs"].append("Restarting Home Assistant")

            restart_result = self._restart_home_assistant(hub_host)
            if restart_result["success"]:
                results["logs"].append("Home Assistant restart initiated")
                logger.info("Home Assistant restart successful")
            else:
                error_msg = f"Failed to restart Home Assistant: {restart_result['error']}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        # Determine final status
        if results["errors"]:
            if results["components_synced"] or results["addons_synced"]:
                results["status"] = "partial_success"
            else:
                results["status"] = "failed"
        else:
            results["status"] = "success"

        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Sync completed with status: {results['status']}")

        return results

    def _rsync_component(
        self,
        component_path: Path,
        component_name: str,
        hub_host: str,
        remote_path: str,
    ) -> Dict:
        """
        Execute rsync for a single component with aggressive sync flags.

        Uses --checksum and --ignore-times to ensure fresh transfers.
        """
        try:
            # Build rsync command with aggressive no-cache options
            cmd = [
                "rsync",
                "-avz",
                "--delete",  # Delete files in destination that don't exist in source
                "--delete-excluded",  # Also delete excluded files
                "--no-inc-recursive",  # Don't use incremental recursion (forces fresh scan)
                "--no-implied-dirs",  # Don't send implied directories
                "--checksum",  # Use checksum instead of mod-time & size
                "--ignore-times",  # Don't skip files that match size and time
                "--exclude=__pycache__/",
                "--exclude=*.pyc",
                "--exclude=.git/",
                "--exclude=.pytest_cache/",
                "--exclude=*.egg-info/",
                "-e", f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                f"{component_path}/",  # Trailing slash is important
                f"{self.ssh_user}@{hub_host}:{remote_path}/{component_name}/",
            ]

            logger.debug(f"Executing rsync command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Rsync failed with no error message",
                    "returncode": result.returncode,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Rsync timeout exceeded (120 seconds)",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _rsync_addon(
        self,
        addon_path: Path,
        addon_name: str,
        hub_host: str,
        remote_path: str,
    ) -> Dict:
        """Execute rsync for a single add-on with aggressive sync flags."""
        try:
            # Build rsync command with aggressive no-cache options
            cmd = [
                "rsync",
                "-avz",
                "--delete",
                "--delete-excluded",
                "--no-inc-recursive",
                "--no-implied-dirs",
                "--checksum",
                "--ignore-times",
                "--exclude=__pycache__/",
                "--exclude=*.pyc",
                "--exclude=.git/",
                "--exclude=.pytest_cache/",
                "-e", f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                f"{addon_path}/",
                f"{self.ssh_user}@{hub_host}:{remote_path}/{addon_name}/",
            ]

            logger.debug(f"Executing rsync command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout for add-ons (can be larger)
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Rsync failed with no error message",
                    "returncode": result.returncode,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Rsync timeout exceeded (180 seconds)",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _restart_home_assistant(self, hub_host: str) -> Dict:
        """Restart Home Assistant via SSH."""
        try:
            cmd = [
                "ssh",
                "-i", self.ssh_key_path,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"{self.ssh_user}@{hub_host}",
                "ha core restart",
            ]

            logger.debug(f"Executing restart command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Restart command failed",
                    "returncode": result.returncode,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Restart command timeout (30 seconds)",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def test_ssh_connection(self, hub_host: str) -> Dict:
        """Test SSH connection to a Yellow hub."""
        try:
            cmd = [
                "ssh",
                "-i", self.ssh_key_path,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                f"{self.ssh_user}@{hub_host}",
                "echo 'Connection successful'",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "SSH connection successful",
                    "output": result.stdout,
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Connection failed",
                    "returncode": result.returncode,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Connection timeout (15 seconds)",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
