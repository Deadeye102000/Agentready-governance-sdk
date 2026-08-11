"""Constants for AgentReady Governance SDK."""

DEFAULT_BASE_URL: str = "http://localhost:3001"
DEFAULT_TIMEOUT: float = 30.0
DEFAULT_MAX_RETRIES: int = 3

# Rate limit defaults (requests per minute) - for reference/client config
DEFAULT_RATE_LIMIT_GENERAL_RPM: int = 300
DEFAULT_RATE_LIMIT_AUTH_RPM: int = 20
