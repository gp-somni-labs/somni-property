"""
Git repository management for Somni component and config delivery.
Adapted from ha-receiver git service for SomniProperty platform.
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List
import git
from git import Repo
import logging

logger = logging.getLogger(__name__)


class GitService:
    """Manages git repositories for Somni component and config delivery."""

    def __init__(self, cache_dir: str = "/app/cache/git"):
        """Initialize GitService with cache directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Get GitHub token for private repos
        github_token = os.getenv("GITHUB_TOKEN", "")
        auth_prefix = f"https://{github_token}@" if github_token else "https://"

        # Repository URLs (will be loaded from env vars in production)
        self.repos = {
            "components": os.getenv(
                "SOMNI_COMPONENTS_REPO",
                f"{auth_prefix}github.com/gp-somni-labs/ha-components.git"
            ),
            "configs": os.getenv(
                "SOMNI_CONFIGS_REPO",
                f"{auth_prefix}github.com/gp-somni-labs/ha-configs.git"
            ),
            "addons": os.getenv(
                "SOMNI_ADDONS_REPO",
                f"{auth_prefix}github.com/gp-somni-labs/ha-addons.git"
            ),
        }

    def _get_repo_path(self, repo_name: str) -> Path:
        """Get local path for repository."""
        return self.cache_dir / repo_name

    def _ensure_repo_cloned(self, repo_name: str) -> Repo:
        """Ensure repository is cloned and up to date."""
        repo_path = self._get_repo_path(repo_name)
        repo_url = self.repos.get(repo_name)

        if not repo_url:
            raise ValueError(f"Unknown repository: {repo_name}")

        # Clone if doesn't exist
        if not repo_path.exists():
            logger.info(f"Cloning {repo_name} from {repo_url}")
            try:
                repo = Repo.clone_from(repo_url, repo_path)
                logger.info(f"Successfully cloned {repo_name}")
            except Exception as e:
                logger.error(f"Failed to clone {repo_name}: {e}")
                raise
        else:
            repo = Repo(repo_path)

        # Pull latest changes
        try:
            logger.info(f"Pulling latest changes for {repo_name}")
            origin = repo.remotes.origin
            origin.pull()
            logger.info(f"Successfully pulled {repo_name}")
        except Exception as e:
            logger.warning(f"Failed to pull {repo_name}: {e}")

        return repo

    def list_components(self) -> List[Dict]:
        """List all available Somni components."""
        try:
            repo = self._ensure_repo_cloned("components")
            repo_path = self._get_repo_path("components")
            components_dir = repo_path / "custom_components"

            if not components_dir.exists():
                logger.warning(f"Components directory not found: {components_dir}")
                return []

            components = []
            for component_path in components_dir.iterdir():
                if component_path.is_dir() and not component_path.name.startswith('.'):
                    # Try to read manifest
                    manifest_path = component_path / "manifest.json"
                    if manifest_path.exists():
                        import json
                        try:
                            with open(manifest_path) as f:
                                manifest = json.load(f)
                                components.append({
                                    "name": component_path.name,
                                    "domain": manifest.get("domain", component_path.name),
                                    "version": manifest.get("version", "unknown"),
                                    "description": manifest.get("name", component_path.name),
                                    "requirements": manifest.get("requirements", []),
                                    "documentation": manifest.get("documentation", ""),
                                })
                        except Exception as e:
                            logger.error(f"Failed to read manifest for {component_path.name}: {e}")
                            # Still add it without manifest data
                            components.append({
                                "name": component_path.name,
                                "domain": component_path.name,
                                "version": "unknown",
                                "description": component_path.name,
                            })
                    else:
                        # Add component without manifest
                        components.append({
                            "name": component_path.name,
                            "domain": component_path.name,
                            "version": "unknown",
                            "description": component_path.name,
                        })

            return components
        except Exception as e:
            logger.error(f"Failed to list components: {e}")
            raise

    def get_component_path(self, component_name: str) -> Optional[Path]:
        """Get path to component directory."""
        try:
            repo = self._ensure_repo_cloned("components")
            repo_path = self._get_repo_path("components")
            component_path = repo_path / "custom_components" / component_name

            if component_path.exists() and component_path.is_dir():
                return component_path

            logger.warning(f"Component not found: {component_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get component path for {component_name}: {e}")
            return None

    def get_component_manifest(self, component_name: str) -> Optional[Dict]:
        """Get component manifest."""
        component_path = self.get_component_path(component_name)
        if not component_path:
            return None

        manifest_path = component_path / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"Manifest not found for component: {component_name}")
            return None

        import json
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read manifest for {component_name}: {e}")
            return None

    def list_configs(self) -> List[Dict]:
        """List all available property configurations."""
        try:
            repo = self._ensure_repo_cloned("configs")
            repo_path = self._get_repo_path("configs")
            configs_dir = repo_path / "configs"

            if not configs_dir.exists():
                logger.warning(f"Configs directory not found: {configs_dir}")
                return []

            configs = []
            for config_path in configs_dir.iterdir():
                if config_path.is_dir() and not config_path.name.startswith('.'):
                    # Try to read config metadata
                    readme_path = config_path / "README.md"
                    description = ""
                    if readme_path.exists():
                        try:
                            with open(readme_path) as f:
                                description = f.read().split('\n')[0]  # First line
                        except Exception:
                            pass

                    configs.append({
                        "name": config_path.name,
                        "path": str(config_path.relative_to(repo_path)),
                        "description": description,
                    })

            return configs
        except Exception as e:
            logger.error(f"Failed to list configs: {e}")
            raise

    def get_config_path(self, config_name: str) -> Optional[Path]:
        """Get path to configuration directory."""
        try:
            repo = self._ensure_repo_cloned("configs")
            repo_path = self._get_repo_path("configs")
            config_path = repo_path / "configs" / config_name

            if config_path.exists() and config_path.is_dir():
                return config_path

            logger.warning(f"Config not found: {config_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get config path for {config_name}: {e}")
            return None

    def list_addons(self) -> List[Dict]:
        """List all available Home Assistant add-ons."""
        try:
            repo = self._ensure_repo_cloned("addons")
            repo_path = self._get_repo_path("addons")
            addons_dir = repo_path / "addons"

            if not addons_dir.exists():
                logger.warning(f"Addons directory not found: {addons_dir}")
                return []

            addons = []
            for addon_path in addons_dir.iterdir():
                if addon_path.is_dir() and not addon_path.name.startswith('.'):
                    # Try to read addon config
                    config_path = addon_path / "config.yaml"
                    addon_info = {
                        "name": addon_path.name,
                        "path": str(addon_path.relative_to(repo_path)),
                    }

                    if config_path.exists():
                        import yaml
                        try:
                            with open(config_path) as f:
                                config = yaml.safe_load(f)
                                addon_info.update({
                                    "display_name": config.get("name", addon_path.name),
                                    "version": config.get("version", "unknown"),
                                    "description": config.get("description", ""),
                                    "arch": config.get("arch", []),
                                })
                        except Exception as e:
                            logger.error(f"Failed to read config for {addon_path.name}: {e}")

                    addons.append(addon_info)

            return addons
        except Exception as e:
            logger.error(f"Failed to list addons: {e}")
            raise

    def get_addon_path(self, addon_name: str) -> Optional[Path]:
        """Get path to add-on directory."""
        try:
            repo = self._ensure_repo_cloned("addons")
            repo_path = self._get_repo_path("addons")
            addon_path = repo_path / "addons" / addon_name

            if addon_path.exists() and addon_path.is_dir():
                return addon_path

            logger.warning(f"Addon not found: {addon_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get addon path for {addon_name}: {e}")
            return None

    def refresh_all(self) -> Dict[str, str]:
        """Refresh all repositories by pulling latest changes."""
        results = {}
        for repo_name in self.repos.keys():
            try:
                logger.info(f"Refreshing repository: {repo_name}")
                self._ensure_repo_cloned(repo_name)
                results[repo_name] = "success"
            except Exception as e:
                logger.error(f"Failed to refresh {repo_name}: {e}")
                results[repo_name] = f"error: {str(e)}"

        return results

    def get_repo_info(self, repo_name: str) -> Optional[Dict]:
        """Get information about a repository."""
        try:
            repo = self._ensure_repo_cloned(repo_name)
            repo_path = self._get_repo_path(repo_name)

            return {
                "name": repo_name,
                "path": str(repo_path),
                "url": self.repos.get(repo_name),
                "branch": repo.active_branch.name,
                "last_commit": repo.head.commit.hexsha[:8],
                "last_commit_message": repo.head.commit.message.strip(),
                "last_commit_date": repo.head.commit.committed_datetime.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get repo info for {repo_name}: {e}")
            return None
