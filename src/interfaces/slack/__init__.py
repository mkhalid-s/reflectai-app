"""
Slack Integration Module for ReflectAI
Mode-Agnostic Slack Integration (Socket Mode + HTTP Mode)

Implements Requirements 12, 16, 22:
- Mode-agnostic design (Socket/HTTP)
- Hybrid threading strategy
- Event processing with deduplication
"""

from .adapter import SlackAdapter
from .app_manifest import (
    SlackEnvironment,
    SlackManifestConfig,
    SlackManifestGenerator,
    export_slack_manifest,
    generate_slack_manifest,
    validate_slack_manifest,
)
from .handlers import SlackCommandHandlers, SlackEventHandlers
from .intelligent_dm import (
    ClarificationGenerator,
    ConversationContextManager,
    IntelligentDMSystem,
    IntentAnalyzer,
    get_intelligent_dm_system,
)
from .response_formatter import ResponseFormatter
from .slash_commands import SlackSlashCommands, get_slash_commands
from .threading import ThreadingManager

__all__ = [
    "SlackAdapter",
    "SlackEventHandlers",
    "SlackCommandHandlers",
    "ThreadingManager",
    "ResponseFormatter",
    # Slash Commands
    "SlackSlashCommands",
    "get_slash_commands",
    # Intelligent DM System
    "IntelligentDMSystem",
    "IntentAnalyzer",
    "ConversationContextManager",
    "ClarificationGenerator",
    "get_intelligent_dm_system",
    # App Manifest
    "SlackManifestGenerator",
    "SlackManifestConfig",
    "SlackEnvironment",
    "generate_slack_manifest",
    "export_slack_manifest",
    "validate_slack_manifest",
]
