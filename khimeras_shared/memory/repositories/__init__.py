"""Domain repositories for the memory package.

Each repository owns one or a few related tables and inherits from
`BaseRepository` (see `../base.py`) to share the connection manager.
The `MemoryStore` facade composes them and exposes the flat legacy API.
"""

from khimeras_shared.memory.repositories.channels import ChannelSummariesRepository
from khimeras_shared.memory.repositories.disclosure import DisclosureRepository
from khimeras_shared.memory.repositories.facts import FactsRepository
from khimeras_shared.memory.repositories.guild_config import GuildConfigRepository
from khimeras_shared.memory.repositories.messages import MessagesRepository
from khimeras_shared.memory.repositories.profiles import ProfilesRepository
from khimeras_shared.memory.repositories.relational import RelationalStateRepository
from khimeras_shared.memory.repositories.reminders import RemindersRepository
from khimeras_shared.memory.repositories.serenityops import SerenityOpsRepository
from khimeras_shared.memory.repositories.world_scans import WorldScansRepository

__all__ = [
    "ChannelSummariesRepository",
    "DisclosureRepository",
    "FactsRepository",
    "GuildConfigRepository",
    "MessagesRepository",
    "ProfilesRepository",
    "RelationalStateRepository",
    "RemindersRepository",
    "SerenityOpsRepository",
    "WorldScansRepository",
]
