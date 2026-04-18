"""LazyGroup implementation for deferred command loading in Raven CLI.

This module provides LazyGroup, a click.Group subclass that defers importing
command modules until they are actually invoked. This improves startup
performance by avoiding loading heavy dependencies (like sentence-transformers)
on every CLI invocation.

Based on Click's official LazyGroup pattern:
https://github.com/pallets/click/blob/main/docs/complex.md
"""

import importlib
from typing import Optional

import click


class LazyGroup(click.Group):
    """A Click Group that lazily loads subcommands.

    Instead of importing all commands at module load time, LazyGroup
    defers the import until a subcommand is actually invoked. This
    allows the CLI to start quickly even when some commands require
    heavy dependencies.

    Example:
        @click.group(
            cls=LazyGroup,
            lazy_subcommands={
                "info": "raven.cli.info:info",
                "cache": "raven.cli.cache:cache",
                "search": "raven.cli.search:search",
            },
        )
        def cli():
            pass
    """

    def __init__(
        self,
        *args: object,
        lazy_subcommands: Optional[dict[str, str]] = None,
        **kwargs: object,
    ) -> None:
        """Initialize LazyGroup.

        Args:
            *args: Positional arguments passed to click.Group.__init__
            lazy_subcommands: Dict mapping command names to import paths.
                           Format: "module.path:command_name"
            **kwargs: Keyword arguments passed to click.Group.__init__
        """
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.lazy_subcommands: dict[str, str] = lazy_subcommands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List all available commands including lazy-loaded ones.

        Args:
            ctx: Click context

        Returns:
            List of command names sorted alphabetically
        """
        # Get built-in commands (if any)
        base_commands: list[str] = super().list_commands(ctx)
        # Get lazy-loaded commands
        lazy_commands = sorted(self.lazy_subcommands.keys())
        return base_commands + lazy_commands

    def get_command(self, ctx: click.Context, name: str) -> Optional[click.Command]:
        """Get a command by name, loading lazily if needed.

        Args:
            ctx: Click context
            name: Command name to look up

        Returns:
            The command if found, None otherwise
        """
        # Check if this is a lazy-loaded command
        if name in self.lazy_subcommands:
            return self._lazy_load(name)
        # Otherwise, look up in parent class
        return super().get_command(ctx, name)

    def _lazy_load(self, name: str) -> click.Command:
        """Lazily load a command by name.

        Args:
            name: Command name (must be in lazy_subcommands)

        Returns:
            The loaded command

        Raises:
            ValueError: If the command cannot be loaded or is not a valid Click command
        """
        import_path = self.lazy_subcommands[name]

        # Parse module path and attribute name
        if ":" not in import_path:
            raise ValueError(
                f"Invalid lazy_subcommands format for '{name}': "
                f"expected 'module.path:command_name', got '{import_path}'"
            )

        modname, cmd_object_name = import_path.rsplit(":", 1)

        # Import the module
        try:
            mod = importlib.import_module(modname)
        except ImportError as e:
            raise ImportError(
                f"Failed to import module '{modname}' for command '{name}': {e}"
            ) from e

        # Get the command object from the module
        cmd_object = getattr(mod, cmd_object_name)

        # Verify it's a valid Click command
        if not isinstance(cmd_object, click.Command):
            raise ValueError(
                f"Lazy loading of '{import_path}' failed: "
                f"expected click.Command, got {type(cmd_object).__name__}"
            )

        return cmd_object
