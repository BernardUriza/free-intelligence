"""Domain repositories for the memory package.

Each repository owns one or a few related tables and inherits from
`BaseRepository` (see `../base.py`) to share the connection manager.
The `MemoryStore` facade composes them and exposes the flat legacy API.
"""

from persona_core.memory.repositories.agendas import AgendasRepository
from persona_core.memory.repositories.agent_facts import AgentFactsRepository
from persona_core.memory.repositories.channels import ChannelSummariesRepository
from persona_core.memory.repositories.disclosure import DisclosureRepository
from persona_core.memory.repositories.facts import FactsRepository
from persona_core.memory.repositories.guild_config import GuildConfigRepository
from persona_core.memory.repositories.invite_turns import InviteTurnsRepository
from persona_core.memory.repositories.messages import MessagesRepository
from persona_core.memory.repositories.profiles import ProfilesRepository
from persona_core.memory.repositories.relational import RelationalStateRepository
from persona_core.memory.repositories.reminders import RemindersRepository
from persona_core.memory.repositories.research_jobs import ResearchJobsRepository
from persona_core.memory.repositories.serenityops import SerenityOpsRepository
from persona_core.memory.repositories.world_scans import WorldScansRepository

__all__ = [
    "AgendasRepository",
    "AgentFactsRepository",
    "ChannelSummariesRepository",
    "DisclosureRepository",
    "FactsRepository",
    "GuildConfigRepository",
    "InviteTurnsRepository",
    "MessagesRepository",
    "ProfilesRepository",
    "RelationalStateRepository",
    "RemindersRepository",
    "ResearchJobsRepository",
    "SerenityOpsRepository",
    "WorldScansRepository",
]
