"""Domain repositories for the memory package.

Each repository owns one or a few related tables and inherits from
`BaseRepository` (see `../base.py`) to share the connection manager.
The `MemoryStore` facade composes them and exposes the flat legacy API.
"""

from insult.core.memory.repositories.channels import ChannelSummariesRepository
from insult.core.memory.repositories.disclosure import DisclosureRepository
from insult.core.memory.repositories.facts import FactsRepository
from insult.core.memory.repositories.guild_config import GuildConfigRepository
from insult.core.memory.repositories.messages import MessagesRepository
from insult.core.memory.repositories.profiles import ProfilesRepository
from insult.core.memory.repositories.relational import RelationalStateRepository
from insult.core.memory.repositories.reminders import RemindersRepository
from insult.core.memory.repositories.serenityops import SerenityOpsRepository
from insult.core.memory.repositories.world_scans import WorldScansRepository

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
