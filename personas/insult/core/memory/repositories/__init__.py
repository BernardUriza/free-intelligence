"""Domain repositories for the memory package.

Each repository owns one or a few related tables and inherits from
`BaseRepository` (see `../base.py`) to share the connection manager.
The `MemoryStore` facade composes them and exposes the flat legacy API.
"""

from personas.insult.core.memory.repositories.channels import ChannelSummariesRepository
from personas.insult.core.memory.repositories.disclosure import DisclosureRepository
from personas.insult.core.memory.repositories.facts import FactsRepository
from personas.insult.core.memory.repositories.guild_config import GuildConfigRepository
from personas.insult.core.memory.repositories.messages import MessagesRepository
from personas.insult.core.memory.repositories.profiles import ProfilesRepository
from personas.insult.core.memory.repositories.relational import RelationalStateRepository
from personas.insult.core.memory.repositories.reminders import RemindersRepository
from personas.insult.core.memory.repositories.serenityops import SerenityOpsRepository
from personas.insult.core.memory.repositories.world_scans import WorldScansRepository

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
