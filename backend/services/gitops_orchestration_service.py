"""
GitOps Orchestration Service for Tier 1/2 deployments.
Commits manifests to client GitOps repos for FluxCD auto-deployment.
"""
import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID
import git
from git import Repo
import yaml

from services.git_service import GitService

logger = logging.getLogger(__name__)


class GitOpsOrchestrationService:
    """Manages GitOps-based deployments for Tier 1/2 hubs via FluxCD."""

    def __init__(self, git_service: Optional[GitService] = None):
        """Initialize GitOpsOrchestrationService."""
        self.git_service = git_service or GitService()
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.git_user_name = os.getenv("GIT_USER_NAME", "SomniProperty Bot")
        self.git_user_email = os.getenv("GIT_USER_EMAIL", "bot@somniproperty.com")

    def deploy_stack_to_client(
        self,
        client_repo_url: str,
        client_repo_branch: str,
        service_package_name: str,
        manifests: Dict[str, str],
        commit_message: Optional[str] = None,
    ) -> Dict:
        """
        Deploy a service package stack to a client's GitOps repository.

        Args:
            client_repo_url: GitHub URL of client's GitOps repo
            client_repo_branch: Branch to commit to (usually main or master)
            service_package_name: Name of service package (e.g., "basic-smart-home")
            manifests: Dict of manifest_filename -> manifest_content (YAML)
            commit_message: Optional custom commit message

        Returns:
            Dict with deployment results
        """
        results = {
            "status": "success",
            "repo_url": client_repo_url,
            "branch": client_repo_branch,
            "package": service_package_name,
            "manifests_committed": [],
            "commit_sha": None,
            "errors": [],
            "logs": [],
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }

        logger.info(f"Starting GitOps deployment for package: {service_package_name}")
        results["logs"].append(f"Starting deployment to {client_repo_url}")

        # Create temporary directory for repo operations
        temp_dir = tempfile.mkdtemp(prefix="gitops_")
        try:
            # Clone client repository
            logger.info(f"Cloning client repository: {client_repo_url}")
            results["logs"].append("Cloning client repository")

            # Add GitHub token to URL if available
            if self.github_token and "github.com" in client_repo_url:
                auth_url = client_repo_url.replace("https://", f"https://{self.github_token}@")
            else:
                auth_url = client_repo_url

            try:
                repo = Repo.clone_from(auth_url, temp_dir, branch=client_repo_branch)
                logger.info("Repository cloned successfully")
                results["logs"].append("Repository cloned successfully")
            except Exception as e:
                error_msg = f"Failed to clone repository: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["status"] = "failed"
                return results

            # Configure git user
            with repo.config_writer() as git_config:
                git_config.set_value("user", "name", self.git_user_name)
                git_config.set_value("user", "email", self.git_user_email)

            # Create manifests directory structure
            manifests_dir = Path(temp_dir) / "manifests" / service_package_name
            manifests_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created manifests directory: {manifests_dir}")
            results["logs"].append(f"Created manifests directory: manifests/{service_package_name}")

            # Write manifests to repo
            for filename, content in manifests.items():
                try:
                    manifest_file = manifests_dir / filename
                    with open(manifest_file, 'w') as f:
                        f.write(content)

                    # Add file to git
                    repo.index.add([str(manifest_file.relative_to(temp_dir))])
                    results["manifests_committed"].append(filename)
                    logger.info(f"Added manifest: {filename}")
                    results["logs"].append(f"Added manifest: {filename}")

                except Exception as e:
                    error_msg = f"Failed to write manifest {filename}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            # Check if there are changes to commit
            if repo.is_dirty() or repo.untracked_files:
                # Commit changes
                if not commit_message:
                    commit_message = f"Deploy {service_package_name} stack\n\nDeployed by SomniProperty at {datetime.utcnow().isoformat()}"

                try:
                    commit = repo.index.commit(commit_message)
                    results["commit_sha"] = commit.hexsha
                    logger.info(f"Created commit: {commit.hexsha[:8]}")
                    results["logs"].append(f"Created commit: {commit.hexsha[:8]}")
                except Exception as e:
                    error_msg = f"Failed to create commit: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["status"] = "failed"
                    return results

                # Push to remote
                try:
                    origin = repo.remote(name='origin')
                    push_info = origin.push(client_repo_branch)

                    # Check push result
                    if push_info and push_info[0].flags & git.remote.PushInfo.ERROR:
                        error_msg = f"Push failed: {push_info[0].summary}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        results["status"] = "failed"
                    else:
                        logger.info("Successfully pushed to remote")
                        results["logs"].append("Successfully pushed to remote repository")
                        results["logs"].append("FluxCD will auto-deploy the changes")

                except Exception as e:
                    error_msg = f"Failed to push to remote: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["status"] = "failed"
                    return results

            else:
                logger.info("No changes to commit")
                results["logs"].append("No changes detected, repository is up to date")
                results["status"] = "no_changes"

        except Exception as e:
            error_msg = f"Unexpected error during GitOps deployment: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            results["status"] = "failed"

        finally:
            # Cleanup temporary directory
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")

        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"GitOps deployment completed with status: {results['status']}")

        return results

    def generate_manifest_from_template(
        self,
        template_name: str,
        template_vars: Dict[str, str],
    ) -> str:
        """
        Generate a Kubernetes manifest from a template.

        Args:
            template_name: Name of the template file
            template_vars: Variables to substitute in template

        Returns:
            Rendered manifest content
        """
        # TODO: Implement template rendering with Jinja2 or similar
        # For now, return a basic template
        logger.warning("Template rendering not yet implemented, returning basic manifest")

        manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": template_vars.get("name", "config"),
                "namespace": template_vars.get("namespace", "default"),
            },
            "data": template_vars,
        }

        return yaml.dump(manifest, default_flow_style=False)

    def deploy_component_manifests(
        self,
        client_repo_url: str,
        client_repo_branch: str,
        component_names: List[str],
    ) -> Dict:
        """
        Deploy Home Assistant component manifests to a client's GitOps repo.

        Args:
            client_repo_url: GitHub URL of client's GitOps repo
            client_repo_branch: Branch to commit to
            component_names: List of component names to deploy

        Returns:
            Dict with deployment results
        """
        results = {
            "status": "success",
            "repo_url": client_repo_url,
            "branch": client_repo_branch,
            "components": component_names,
            "errors": [],
            "logs": [],
        }

        logger.info(f"Deploying {len(component_names)} components via GitOps")
        results["logs"].append(f"Preparing to deploy {len(component_names)} components")

        # Generate ConfigMap manifests for each component
        manifests = {}

        for component_name in component_names:
            try:
                # Get component metadata
                component_manifest = self.git_service.get_component_manifest(component_name)

                # Generate ConfigMap manifest
                # In production, this would create proper Kubernetes manifests
                # for deploying the component to Home Assistant pods
                manifest_content = self._generate_component_configmap(
                    component_name=component_name,
                    component_manifest=component_manifest,
                )

                manifests[f"{component_name}-config.yaml"] = manifest_content
                results["logs"].append(f"Generated manifest for: {component_name}")

            except Exception as e:
                error_msg = f"Failed to generate manifest for {component_name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        # Deploy all manifests
        if manifests:
            deploy_result = self.deploy_stack_to_client(
                client_repo_url=client_repo_url,
                client_repo_branch=client_repo_branch,
                service_package_name="ha-components",
                manifests=manifests,
                commit_message=f"Deploy Somni components: {', '.join(component_names)}",
            )

            results.update(deploy_result)
        else:
            results["status"] = "failed"
            results["errors"].append("No manifests generated")

        return results

    def _generate_component_configmap(
        self,
        component_name: str,
        component_manifest: Optional[Dict],
    ) -> str:
        """Generate a ConfigMap manifest for a component."""
        # In a real implementation, this would:
        # 1. Package the component files into a ConfigMap or PVC
        # 2. Create an init container to copy files to HA pod
        # 3. Configure proper volume mounts

        config = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"ha-component-{component_name}",
                "namespace": "home-assistant",
                "labels": {
                    "app": "home-assistant",
                    "component": component_name,
                    "managed-by": "somniproperty",
                },
            },
            "data": {
                "component_name": component_name,
                "version": component_manifest.get("version", "unknown") if component_manifest else "unknown",
                "domain": component_manifest.get("domain", component_name) if component_manifest else component_name,
            },
        }

        return yaml.dump(config, default_flow_style=False)

    def rollback_deployment(
        self,
        client_repo_url: str,
        client_repo_branch: str,
        commit_sha: str,
    ) -> Dict:
        """
        Rollback a deployment by reverting to a previous commit.

        Args:
            client_repo_url: GitHub URL of client's GitOps repo
            client_repo_branch: Branch to rollback
            commit_sha: Commit SHA to revert to

        Returns:
            Dict with rollback results
        """
        results = {
            "status": "success",
            "repo_url": client_repo_url,
            "branch": client_repo_branch,
            "reverted_to": commit_sha,
            "errors": [],
            "logs": [],
        }

        logger.info(f"Rolling back to commit: {commit_sha}")
        results["logs"].append(f"Initiating rollback to {commit_sha[:8]}")

        temp_dir = tempfile.mkdtemp(prefix="gitops_rollback_")
        try:
            # Add GitHub token to URL if available
            if self.github_token and "github.com" in client_repo_url:
                auth_url = client_repo_url.replace("https://", f"https://{self.github_token}@")
            else:
                auth_url = client_repo_url

            # Clone repository
            repo = Repo.clone_from(auth_url, temp_dir, branch=client_repo_branch)

            # Configure git user
            with repo.config_writer() as git_config:
                git_config.set_value("user", "name", self.git_user_name)
                git_config.set_value("user", "email", self.git_user_email)

            # Revert to specified commit
            repo.git.revert(commit_sha, no_edit=True)

            # Push changes
            origin = repo.remote(name='origin')
            origin.push(client_repo_branch)

            results["logs"].append("Rollback successful")
            logger.info("Rollback completed successfully")

        except Exception as e:
            error_msg = f"Rollback failed: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            results["status"] = "failed"

        finally:
            # Cleanup
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")

        return results
