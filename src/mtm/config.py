"""Configuration management for meeting-to-modules."""

from pathlib import Path

import toml
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Application configuration loaded from TOML file."""

    input_dirs: list[str] = Field(default_factory=lambda: ["data/seed/notes"])
    output_dir: str = "outputs"
    db_path: str = "outputs/mtm.db"
    language: str = "en"
    min_theme_support: int = 3
    kmeans_k: int = 6
    redact_rules: str | None = None
    role_taxonomy: str = "default"
    enable_pdf_to_text: bool = True

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Config":
        """Load configuration from TOML file.

        Args:
            config_path: Path to config file. Defaults to configs/config.toml

        Returns:
            Config instance with loaded values
        """
        if config_path is None:
            # Default to configs/config.toml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "configs" / "config.toml"
        else:
            config_path = Path(config_path)

        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load config if it exists, otherwise use defaults
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = toml.load(f)
            # Extract config from [mtm] section if present, otherwise use root
            config_dict = config_data.get("mtm", config_data)
        else:
            config_dict = {}

        # Create config instance
        config = cls(**config_dict)

        # Ensure all directories exist
        config.ensure_directories()

        return config

    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        # Ensure input directories exist
        for input_dir in self.input_dirs:
            Path(input_dir).mkdir(parents=True, exist_ok=True)

        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Ensure database directory exists
        db_path = Path(self.db_path)
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, config_path: str | Path | None = None) -> None:
        """Save current configuration to TOML file.

        Args:
            config_path: Path to save config. Defaults to configs/config.toml
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "configs" / "config.toml"
        else:
            config_path = Path(config_path)

        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and wrap in [mtm] section
        config_dict = {"mtm": self.model_dump()}

        # Write to file
        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(config_dict, f)


# Global config instance (lazy loaded)
_config: Config | None = None


def get_config(config_path: str | Path | None = None) -> Config:
    """Get or create global configuration instance.

    Args:
        config_path: Path to config file. Only used on first call.

    Returns:
        Global Config instance
    """
    global _config
    if _config is None:
        _config = Config.load(config_path)
    return _config

