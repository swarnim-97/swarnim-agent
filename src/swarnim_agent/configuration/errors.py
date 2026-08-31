class ConfigurationError(Exception):
    """Base error for configuration that prevents application startup."""


class MissingConfigurationError(ConfigurationError):
    """Raised when the user configuration file does not exist."""


class MissingCredentialError(ConfigurationError):
    """Raised when the selected provider credential cannot be resolved."""


class UnsupportedProviderError(ConfigurationError):
    """Raised when configuration selects an unavailable provider or API mode."""
