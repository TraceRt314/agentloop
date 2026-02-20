"""Plugin system for AgentLoop.

Discovers, loads, and manages plugins from the plugins directory.
Each plugin is a directory containing a ``plugin.yaml`` manifest and
Python modules that provide routes, hooks, and optional SQLModel models.
"""

import importlib
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import yaml
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Manifest schema ──────────────────────────────────────────────


class FrontendTab(BaseModel):
    """A tab that the plugin contributes to the frontend."""

    id: str
    label: str
    icon: str = ""
    component_path: str = ""


class PluginManifest(BaseModel):
    """Parsed ``plugin.yaml`` for a single plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    depends_on: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    routes: List[str] = Field(default_factory=list)
    hooks: List[str] = Field(default_factory=list)
    frontend_tabs: List[FrontendTab] = Field(default_factory=list)
    config_schema: Dict[str, Any] = Field(default_factory=dict)


# ── Loaded plugin ────────────────────────────────────────────────


@dataclass
class LoadedPlugin:
    """A fully-resolved plugin ready to register."""

    manifest: PluginManifest
    path: Path
    routers: List[APIRouter] = field(default_factory=list)
    hook_callables: Dict[str, List[Callable]] = field(default_factory=dict)
    model_classes: List[Any] = field(default_factory=list)


# ── Plugin manager ───────────────────────────────────────────────


class PluginManager:
    """Discovers, loads, and manages AgentLoop plugins."""

    def __init__(self, plugins_dir: str = "./plugins", enabled: str = ""):
        self.plugins_dir = Path(plugins_dir)
        self.enabled_filter: Optional[List[str]] = (
            [s.strip() for s in enabled.split(",") if s.strip()]
            if enabled
            else None
        )
        self.plugins: Dict[str, LoadedPlugin] = {}

    # ── Discovery ────────────────────────────────────────────

    def discover(self) -> List[PluginManifest]:
        """Scan ``plugins_dir`` for directories containing ``plugin.yaml``."""
        manifests: List[PluginManifest] = []
        if not self.plugins_dir.exists():
            logger.debug("Plugins directory %s does not exist", self.plugins_dir)
            return manifests

        for child in sorted(self.plugins_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_file = child / "plugin.yaml"
            if not manifest_file.exists():
                continue
            try:
                with open(manifest_file) as f:
                    raw = yaml.safe_load(f) or {}
                manifest = PluginManifest(**raw)
                manifests.append(manifest)
            except Exception:
                logger.warning("Skipping invalid manifest: %s", manifest_file)
        return manifests

    # ── Loading ──────────────────────────────────────────────

    def load_all(self) -> None:
        """Discover and load all enabled plugins in dependency order."""
        manifests = self.discover()
        if self.enabled_filter is not None:
            manifests = [m for m in manifests if m.name in self.enabled_filter]

        ordered = self._topological_sort(manifests)

        for manifest in ordered:
            try:
                loaded = self._load_plugin(manifest)
                self.plugins[manifest.name] = loaded
                logger.info("Loaded plugin: %s v%s", manifest.name, manifest.version)
            except Exception:
                logger.exception("Failed to load plugin: %s", manifest.name)

    def _load_plugin(self, manifest: PluginManifest) -> LoadedPlugin:
        """Import a single plugin's modules and resolve references."""
        plugin_dir = self.plugins_dir / manifest.name
        # Sanitise plugin name for use as a Python identifier
        safe_name = manifest.name.replace("-", "_")

        # Register the plugin directory as a package under a unique namespace
        # so that ``routes.dashboard`` in mission-control doesn't collide with
        # ``routes.tasks`` in the tasks plugin.
        self._register_plugin_package(plugin_dir, safe_name)

        # Also add the plugin dir to sys.path so that bare imports like
        # ``from models import X`` work inside plugin route/hook modules.
        dir_str = str(plugin_dir)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)

        routers: List[APIRouter] = []
        hook_callables: Dict[str, List[Callable]] = {}
        model_classes: List[Any] = []

        # Load route modules
        for route_ref in manifest.routes:
            fqn = f"_agentloop_plugins.{safe_name}.{route_ref}"
            module = self._import_plugin_module(plugin_dir, route_ref, fqn)
            if hasattr(module, "router"):
                routers.append(module.router)

        # Load hook modules
        for hook_ref in manifest.hooks:
            fqn = f"_agentloop_plugins.{safe_name}.{hook_ref}"
            module = self._import_plugin_module(plugin_dir, hook_ref, fqn)
            # Convention: each hook module defines HOOKS = {"hook_name": callable}
            hooks_map: Dict[str, Callable] = getattr(module, "HOOKS", {})
            for hook_name, fn in hooks_map.items():
                hook_callables.setdefault(hook_name, []).append(fn)

        # Load model modules (for create_all)
        for model_ref in manifest.models:
            fqn = f"_agentloop_plugins.{safe_name}.{model_ref}"
            module = self._import_plugin_module(plugin_dir, model_ref, fqn)
            # Collect all SQLModel subclasses from the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "__tablename__")
                    and attr.__name__ not in ("SQLModel",)
                ):
                    model_classes.append(attr)

        return LoadedPlugin(
            manifest=manifest,
            path=plugin_dir,
            routers=routers,
            hook_callables=hook_callables,
            model_classes=model_classes,
        )

    # ── Module import helpers ─────────────────────────────────

    @staticmethod
    def _register_plugin_package(plugin_dir: Path, safe_name: str) -> None:
        """Create synthetic package entries so sub-module imports resolve."""
        import types

        # Ensure the top-level namespace package exists
        ns = "_agentloop_plugins"
        if ns not in sys.modules:
            pkg = types.ModuleType(ns)
            pkg.__path__ = []  # namespace package
            pkg.__package__ = ns
            sys.modules[ns] = pkg

        # Register the plugin itself as a sub-package
        pkg_fqn = f"{ns}.{safe_name}"
        if pkg_fqn not in sys.modules:
            pkg = types.ModuleType(pkg_fqn)
            pkg.__path__ = [str(plugin_dir)]
            pkg.__package__ = pkg_fqn
            sys.modules[pkg_fqn] = pkg

    @staticmethod
    def _import_plugin_module(plugin_dir: Path, dotted_ref: str, fqn: str) -> Any:
        """Import *dotted_ref* relative to *plugin_dir* under the given fqn.

        For example ``routes.dashboard`` → ``plugin_dir/routes/dashboard.py``
        registered as ``_agentloop_plugins.mission_control.routes.dashboard``.
        """
        import importlib.util
        import types

        parts = dotted_ref.split(".")
        # Resolve the file path
        candidate = plugin_dir / "/".join(parts)
        if candidate.is_dir():
            file_path = candidate / "__init__.py"
        else:
            file_path = plugin_dir / "/".join(parts[:-1] + [parts[-1] + ".py"])
            if not file_path.exists():
                file_path = candidate / "__init__.py"

        # Ensure intermediate packages exist in sys.modules
        for i in range(1, len(parts)):
            intermediate = ".".join(fqn.split(".")[:-(len(parts) - i)])
            sub_parts = parts[:i]
            inter_fqn = f"{intermediate}.{'.'.join(sub_parts)}" if intermediate else fqn.rsplit(".", len(parts) - i)[0]
            # Simpler: build from the namespace root
            inter_fqn = f"_agentloop_plugins.{fqn.split('.')[1]}.{'.'.join(sub_parts)}"
            if inter_fqn not in sys.modules:
                inter_dir = plugin_dir / "/".join(sub_parts)
                pkg = types.ModuleType(inter_fqn)
                pkg.__path__ = [str(inter_dir)]
                pkg.__package__ = inter_fqn
                sys.modules[inter_fqn] = pkg

        spec = importlib.util.spec_from_file_location(fqn, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot find module {dotted_ref} at {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[fqn] = module
        spec.loader.exec_module(module)
        return module

    # ── Registration ─────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        """Mount all plugin routers onto the FastAPI app."""
        for name, plugin in self.plugins.items():
            for router in plugin.routers:
                app.include_router(router)
                logger.debug("Mounted router from plugin %s", name)

    # ── Hooks ────────────────────────────────────────────────

    def dispatch_hook(self, name: str, **kwargs: Any) -> List[Any]:
        """Call all registered hooks for *name*, passing **kwargs.

        Returns a list of return values (one per handler).
        Exceptions in individual handlers are logged but do not
        prevent subsequent handlers from running.
        """
        results: List[Any] = []
        for plugin_name, plugin in self.plugins.items():
            for fn in plugin.hook_callables.get(name, []):
                try:
                    results.append(fn(**kwargs))
                except Exception:
                    logger.exception(
                        "Hook %s from plugin %s failed", name, plugin_name
                    )
        return results

    # ── Query helpers ────────────────────────────────────────

    def get_frontend_tabs(self) -> List[Dict[str, Any]]:
        """Return tab metadata from all loaded plugins."""
        tabs: List[Dict[str, Any]] = []
        for name, plugin in self.plugins.items():
            for tab in plugin.manifest.frontend_tabs:
                tabs.append({
                    "plugin": name,
                    "id": tab.id,
                    "label": tab.label,
                    "icon": tab.icon,
                    "component_path": tab.component_path,
                })
        return tabs

    def has_plugin(self, name: str) -> bool:
        """Check if a plugin is loaded by name."""
        return name in self.plugins

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Return summary info for all loaded plugins."""
        return [
            {
                "name": name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "hooks": list(p.hook_callables.keys()),
                "routes": len(p.routers),
                "models": len(p.model_classes),
                "frontend_tabs": [t.id for t in p.manifest.frontend_tabs],
            }
            for name, p in self.plugins.items()
        ]

    # ── Dependency resolution ────────────────────────────────

    @staticmethod
    def _topological_sort(manifests: Sequence[PluginManifest]) -> List[PluginManifest]:
        """Sort manifests so that dependencies come first (Kahn's algorithm)."""
        by_name = {m.name: m for m in manifests}
        in_degree: Dict[str, int] = {m.name: 0 for m in manifests}
        dependents: Dict[str, List[str]] = {m.name: [] for m in manifests}

        for m in manifests:
            for dep in m.depends_on:
                if dep in by_name:
                    in_degree[m.name] += 1
                    dependents[dep].append(m.name)
                else:
                    # Dependency not in manifest set — mark as unsatisfiable
                    in_degree[m.name] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        result: List[PluginManifest] = []

        while queue:
            node = queue.pop(0)
            result.append(by_name[node])
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Anything left has unsatisfied deps — skip with warning
        loaded_names = {m.name for m in result}
        for m in manifests:
            if m.name not in loaded_names:
                logger.warning(
                    "Plugin %s skipped: unsatisfied dependencies %s",
                    m.name,
                    [d for d in m.depends_on if d not in loaded_names],
                )

        return result
