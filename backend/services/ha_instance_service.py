"""
Home Assistant Instance Service
Handles status checks, SSH operations, and component management.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas_ha_instance import HAInstanceStatus
from db.database import AsyncSessionLocal


# Configuration from environment
SSH_KEY_PATH = os.environ.get("HA_SSH_KEY_PATH", "/etc/secrets/ha-master-key/id_rsa")
FERNET_KEY = os.environ.get("FERNET_KEY", Fernet.generate_key().decode())


class HAInstanceService:
    """Service for managing Home Assistant instances."""

    def __init__(self):
        self._fernet = Fernet(FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY)

    def encrypt_api_token(self, token: str) -> str:
        """Encrypt an API token for storage."""
        return self._fernet.encrypt(token.encode()).decode()

    def decrypt_api_token(self, encrypted_token: str) -> str:
        """Decrypt an API token from storage."""
        return self._fernet.decrypt(encrypted_token.encode()).decode()

    async def check_instance_status(self, instance) -> HAInstanceStatus:
        """
        Check HA instance status via SSH.

        Executes 'ha core info' to get version and health.
        """
        try:
            result = await asyncio.wait_for(
                self._ssh_ha_info(
                    host=instance.host,
                    user=instance.ssh_user,
                    port=instance.ssh_port
                ),
                timeout=15.0
            )

            return HAInstanceStatus(
                online=True,
                ha_version=result.get("version"),
                supervisor_version=result.get("supervisor"),
                os_type=result.get("machine"),
                uptime_seconds=result.get("uptime"),
                healthy=result.get("healthy", False),
                last_checked=datetime.now(timezone.utc)
            )

        except asyncio.TimeoutError:
            return HAInstanceStatus(
                online=False,
                healthy=False,
                last_checked=datetime.now(timezone.utc),
                error="Connection timeout (15s)"
            )
        except Exception as e:
            return HAInstanceStatus(
                online=False,
                healthy=False,
                last_checked=datetime.now(timezone.utc),
                error=str(e)
            )

    async def _ssh_ha_info(self, host: str, user: str, port: int) -> dict:
        """Execute 'ha core info' via SSH and parse result."""
        ssh_cmd = [
            "ssh",
            "-i", SSH_KEY_PATH,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes",
            f"{user}@{host}",
            "-p", str(port),
            "ha", "core", "info", "--raw-json"
        ]

        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else f"SSH returned {proc.returncode}"
            raise Exception(f"SSH command failed: {error_msg}")

        try:
            data = json.loads(stdout.decode())
            return data.get("data", data)
        except json.JSONDecodeError:
            # Try parsing as plain text (some HA versions)
            lines = stdout.decode().strip().split("\n")
            result = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    result[key.strip().lower()] = value.strip()
            return result

    async def check_multiple_status(self, instances: List) -> Dict[str, HAInstanceStatus]:
        """Check status of multiple instances in parallel."""
        tasks = {
            str(instance.id): self.check_instance_status(instance)
            for instance in instances
        }

        results = {}
        for instance_id, task in tasks.items():
            try:
                results[instance_id] = await task
            except Exception as e:
                results[instance_id] = HAInstanceStatus(
                    online=False,
                    healthy=False,
                    last_checked=datetime.now(timezone.utc),
                    error=str(e)
                )

        return results

    async def get_installed_components(self, instance) -> Dict[str, bool]:
        """
        Get installed Somni components on an HA instance.

        Checks /config/custom_components directory for somni_* folders.
        """
        try:
            ssh_cmd = [
                "ssh",
                "-i", SSH_KEY_PATH,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-o", "BatchMode=yes",
                f"{instance.ssh_user}@{instance.host}",
                "-p", str(instance.ssh_port),
                "ls", "-1", "/config/custom_components/"
            ]

            proc = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {}

            # Parse installed components
            installed = stdout.decode().strip().split("\n")

            # Known Somni components
            somni_components = [
                "somni_property_sync",
                "somni_lights",
                "somni_access",
                "somni_security",
                "somni_occupancy",
                "somni_climate",
                "somni_maintenance",
                "somni_alerts",
                "somni_voice",
                "somni_energy",
                "somni_water",
                "somni_lease_automation"
            ]

            return {
                comp: comp in installed
                for comp in somni_components
            }

        except Exception:
            return {}

    async def execute_ssh_command(
        self,
        instance,
        command: str,
        timeout: int = 30
    ) -> dict:
        """
        Execute a command on an HA instance via SSH.

        Returns stdout, stderr, and exit code.
        """
        try:
            ssh_cmd = [
                "ssh",
                "-i", SSH_KEY_PATH,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-o", "BatchMode=yes",
                f"{instance.ssh_user}@{instance.host}",
                "-p", str(instance.ssh_port),
                command
            ]

            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *ssh_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=timeout
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )

            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "exit_code": proc.returncode,
                "success": proc.returncode == 0
            }

        except asyncio.TimeoutError:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }

    async def perform_log_analysis(
        self,
        analysis_id: UUID,
        question: str,
        instance_ids: List[UUID]
    ):
        """
        Background task: Fetch logs and run Claude analysis.

        Updates the HALogAnalysis record with results.
        """
        from db.models import HAInstance, HALogAnalysis

        async with AsyncSessionLocal() as db:
            try:
                # Update status to analyzing
                await db.execute(
                    update(HALogAnalysis)
                    .where(HALogAnalysis.id == analysis_id)
                    .values(
                        analysis_status="analyzing",
                        started_at=datetime.now(timezone.utc)
                    )
                )
                await db.commit()

                # Get instances
                from sqlalchemy import select
                instances = []
                for iid in instance_ids:
                    result = await db.execute(
                        select(HAInstance).where(HAInstance.id == iid)
                    )
                    instance = result.scalar_one_or_none()
                    if instance:
                        instances.append(instance)

                # Fetch logs from each instance
                logs = {}
                total_lines = 0
                for instance in instances:
                    log_result = await self.execute_ssh_command(
                        instance,
                        "tail -n 500 /config/home-assistant.log",
                        timeout=30
                    )
                    if log_result["success"]:
                        logs[instance.name] = log_result["stdout"]
                        total_lines += len(log_result["stdout"].split("\n"))

                # Prepare Claude prompt
                log_content = "\n\n".join(
                    f"=== {name} ===\n{log}"
                    for name, log in logs.items()
                )

                prompt = f"""Analyze these Home Assistant logs and answer: {question}

{log_content}

If you identify actionable fixes, format them as:
SUGGESTED_COMMAND: instance_name | command | reason

Be specific about which instance each command should run on.
"""

                # Call Claude API
                analysis_result = await self._call_claude_api(prompt)

                # Parse suggested commands
                suggested_commands = self._parse_suggested_commands(analysis_result)

                # Update database with results
                now = datetime.now(timezone.utc)
                await db.execute(
                    update(HALogAnalysis)
                    .where(HALogAnalysis.id == analysis_id)
                    .values(
                        analysis_status="completed",
                        analysis_text=analysis_result,
                        suggested_commands=suggested_commands,
                        logs_reviewed_count=total_lines,
                        completed_at=now,
                        duration_seconds=int((now - datetime.now(timezone.utc)).total_seconds())
                    )
                )
                await db.commit()

                # Create command approval records for suggested commands
                from db.models import HACommandApproval
                for cmd in suggested_commands:
                    # Find target instance
                    target = next(
                        (i for i in instances if i.name == cmd.get("instance")),
                        instances[0] if instances else None
                    )
                    if target:
                        approval = HACommandApproval(
                            analysis_id=analysis_id,
                            target_instance_id=target.id,
                            command=cmd.get("command", ""),
                            reason=cmd.get("reason", ""),
                            approval_status="pending"
                        )
                        db.add(approval)

                await db.commit()

            except Exception as e:
                await db.execute(
                    update(HALogAnalysis)
                    .where(HALogAnalysis.id == analysis_id)
                    .values(
                        analysis_status="failed",
                        error_message=str(e)
                    )
                )
                await db.commit()

    async def _call_claude_api(self, prompt: str) -> str:
        """Call Claude API for log analysis."""
        # Try using anthropic library first
        try:
            import anthropic

            client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY", "")
            )

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except ImportError:
            # Fallback to Claude Code CLI
            result = await self.execute_ssh_command(
                type("MockInstance", (), {
                    "host": "localhost",
                    "ssh_user": os.environ.get("USER", "root"),
                    "ssh_port": 22
                })(),
                f'claude --print "{prompt[:500]}..."',
                timeout=60
            )
            return result.get("stdout", "Analysis unavailable - Claude API not configured")

        except Exception as e:
            return f"Analysis failed: {str(e)}"

    def _parse_suggested_commands(self, analysis_text: str) -> List[Dict[str, str]]:
        """Parse SUGGESTED_COMMAND lines from Claude response."""
        commands = []

        for line in analysis_text.split("\n"):
            if line.strip().startswith("SUGGESTED_COMMAND:"):
                try:
                    parts = line.split(":", 1)[1].strip().split("|")
                    if len(parts) >= 2:
                        commands.append({
                            "instance": parts[0].strip(),
                            "command": parts[1].strip(),
                            "reason": parts[2].strip() if len(parts) > 2 else ""
                        })
                except Exception:
                    continue

        return commands

    async def execute_approved_command(self, command_id: UUID):
        """
        Background task: Execute an approved command.

        Updates the HACommandApproval record with results.
        """
        from db.models import HAInstance, HACommandApproval

        async with AsyncSessionLocal() as db:
            try:
                from sqlalchemy import select

                # Get command
                result = await db.execute(
                    select(HACommandApproval).where(HACommandApproval.id == command_id)
                )
                command = result.scalar_one_or_none()

                if not command or command.approval_status != "approved":
                    return

                # Get target instance
                result = await db.execute(
                    select(HAInstance).where(HAInstance.id == command.target_instance_id)
                )
                instance = result.scalar_one_or_none()

                if not instance:
                    await db.execute(
                        update(HACommandApproval)
                        .where(HACommandApproval.id == command_id)
                        .values(
                            approval_status="failed",
                            execution_output="Target instance not found"
                        )
                    )
                    await db.commit()
                    return

                # Execute command
                exec_result = await self.execute_ssh_command(
                    instance,
                    command.command,
                    timeout=60
                )

                # Update command record
                await db.execute(
                    update(HACommandApproval)
                    .where(HACommandApproval.id == command_id)
                    .values(
                        approval_status="executed" if exec_result["success"] else "failed",
                        executed_at=datetime.now(timezone.utc),
                        execution_output=exec_result["stdout"] + exec_result["stderr"],
                        exit_code=exec_result["exit_code"]
                    )
                )
                await db.commit()

            except Exception as e:
                await db.execute(
                    update(HACommandApproval)
                    .where(HACommandApproval.id == command_id)
                    .values(
                        approval_status="failed",
                        execution_output=str(e)
                    )
                )
                await db.commit()
