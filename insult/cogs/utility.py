"""Utility commands: ping, memoria, buscar, facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
import structlog
from discord.ext import commands

from insult.core.errors import ErrorType, get_error_response
from insult.core.facts import extract_facts
from insult.core.guild_setup import setup_guild

if TYPE_CHECKING:
    from insult.app import Container

log = structlog.get_logger()


class UtilityCog(commands.Cog):
    def __init__(self, container: Container):
        self.memory = container.memory
        self.llm = container.llm
        self.settings = container.settings
        self.bot = container.bot
        self.siesta = container.siesta

    @commands.command(name="perfil")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def perfil(self, ctx: commands.Context):
        """Muestra tu perfil de estilo — como te ve Insult."""
        user_id = str(ctx.author.id)
        try:
            profile = await self.memory.get_profile(user_id)
        except Exception:
            log.exception("perfil_failed", user_id=user_id)
            await ctx.send(get_error_response(ErrorType.GENERIC))
            return

        if not profile.is_confident:
            await ctx.send(
                f"Todavia no te conozco bien, {ctx.author.display_name}. "
                f"Llevas {profile.message_count} mensajes — necesito al menos 5 para formarte un perfil. "
                f"Sigue hablando y veremos que tipo de especimen eres."
            )
            return

        lang = "espanol" if profile.detected_language == "es" else "ingles"
        formality_desc = (
            "hablas como camionero"
            if profile.formality < 0.25
            else "eres medio formal"
            if profile.formality < 0.6
            else "hablas como si fueras a una entrevista de trabajo"
        )
        tech_desc = (
            "no sabes ni que es una variable"
            if profile.technical_level < 0.2
            else "sabes lo basico"
            if profile.technical_level < 0.5
            else "le sabes al codigo"
            if profile.technical_level < 0.7
            else "eres un nerd de los pesados"
        )
        verbose_desc = (
            "escribes telegrama"
            if profile.avg_word_count < 10
            else "escribes normal"
            if profile.avg_word_count < 30
            else "escribes biblias"
        )

        await ctx.send(
            f"**Tu perfil segun yo, {ctx.author.display_name}:**\n"
            f"- Idioma: {lang}\n"
            f"- Estilo: {formality_desc}\n"
            f"- Nivel tecnico: {tech_desc}\n"
            f"- Verbosidad: {verbose_desc} (~{profile.avg_word_count:.0f} palabras/msg)\n"
            f"- Emojis: {'si usas' if profile.emoji_ratio > 0.05 else 'ni los tocas'}\n"
            f"- Mensajes analizados: {profile.message_count}\n\n"
            f"*Y si, ajusto como te hablo segun esto. Algun problema con eso?*"
        )

    @commands.command(name="ping")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"Pong! {round(self.bot.latency * 1000)}ms")

    @commands.command(name="siesta")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def siesta_command(self, ctx: commands.Context):
        """Muestra el diario del último sueño y, si está dormido, su progreso."""
        from insult.core.siesta.diary.storage import latest_entry

        snapshot = self.siesta.get()
        lines: list[str] = []
        if snapshot.is_active:
            elapsed_min = snapshot.elapsed_seconds // 60
            elapsed_sec = snapshot.elapsed_seconds % 60
            lines.append(
                f"🛌 Estoy dormido — fase **{snapshot.phase.value}**, "
                f"{snapshot.processed_users}/{snapshot.total_users} usuarios "
                f"({snapshot.progress_pct}%), llevo {elapsed_min}m {elapsed_sec}s."
            )
            if snapshot.current_user_id:
                lines.append(f"   Soñando con `{snapshot.current_user_id}` ahorita.")
            lines.append("")

        try:
            entry = await latest_entry(self.memory)
        except Exception:
            log.exception("siesta_command_diary_failed")
            entry = None

        if entry is None:
            lines.append("Todavia no tengo nada en el diario. La primera siesta llega pronto.")
        else:
            import time as _time

            ago = max(0, int((_time.time() - entry.run_ts) / 60))
            ago_str = f"hace {ago}m" if ago < 60 else f"hace {ago // 60}h {ago % 60}m"
            lines.append(f"**Última siesta** ({ago_str}, duró {entry.duration_ms // 1000}s, status `{entry.status}`):")
            lines.append(f"> {entry.content}")

        await ctx.send("\n".join(lines))

    @commands.command(name="memoria")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def memoria(self, ctx: commands.Context):
        """Muestra stats de memoria del canal."""
        try:
            stats = await self.memory.get_stats(str(ctx.channel.id))
            await ctx.send(
                f"**Memoria de este canal:**\n"
                f"- Mensajes: {stats['total_messages']}\n"
                f"- Usuarios: {stats['unique_users']}"
            )
        except Exception:
            log.exception("memoria_failed", channel_id=str(ctx.channel.id))
            await ctx.send(get_error_response(ErrorType.GENERIC))

    @commands.command(name="buscar")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def buscar(self, ctx: commands.Context, *, query: str):
        """Busca en la memoria longitudinal del canal."""
        try:
            results = await self.memory.search(str(ctx.channel.id), query, limit=10)
        except Exception:
            log.exception("buscar_failed", channel_id=str(ctx.channel.id), query=query)
            await ctx.send(get_error_response(ErrorType.CONTEXT_FAILED))
            return

        if not results:
            await ctx.send("No encontre nada.")
            return

        lines = [f"**{r['user_name']}:** {r['content'][:100]}" for r in results]
        await ctx.send(f"**Resultados para '{query}':**\n" + "\n".join(lines))

    @commands.command(name="facts")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def facts(self, ctx: commands.Context, member: commands.MemberConverter | None = None):
        """Muestra los facts de un usuario. Sin argumento = tus facts. Con @mention = facts de esa persona."""
        target = member or ctx.author
        user_id = str(target.id)
        display_name = target.display_name

        try:
            user_facts = await self.memory.get_facts(user_id)
        except Exception:
            log.exception("facts_command_failed", user_id=user_id)
            await ctx.send(get_error_response(ErrorType.GENERIC))
            return

        if not user_facts:
            await ctx.send(f"No tengo facts de **{display_name}**. Que hable más y los voy juntando.")
            return

        # Group by category
        by_cat: dict[str, list[str]] = {}
        for f in user_facts:
            by_cat.setdefault(f["category"], []).append(f["fact"])

        cat_emojis = {
            "identity": "🏷️",
            "profession": "💼",
            "location": "📍",
            "interests": "🎮",
            "technical": "💻",
            "personal": "🧠",
            "preferences": "⭐",
            "general": "📝",
        }

        lines = [f"**Facts de {display_name}:**\n"]
        for cat, facts_list in by_cat.items():
            emoji = cat_emojis.get(cat, "📝")
            lines.append(f"{emoji} **{cat.title()}**")
            for fact in facts_list:
                lines.append(f"  → {fact}")

        lines.append(f"\n*Total: {len(user_facts)} facts*")
        await ctx.send("\n".join(lines))

    @commands.command(name="syncfacts")
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def syncfacts(self, ctx: commands.Context):
        """Recorre todos los mensajes históricos y extrae/actualiza facts de cada usuario."""
        await ctx.send("🔄 Sincronizando facts de todos los usuarios... esto puede tardar.")

        try:
            user_data = await self.memory.get_all_user_messages(limit_per_user=30)
        except Exception:
            log.exception("syncfacts_get_messages_failed")
            await ctx.send(get_error_response(ErrorType.GENERIC))
            return

        synced = 0
        errors = 0
        for user_id, data in user_data.items():
            user_name = data["user_name"]
            messages = data["messages"]
            if not messages:
                continue

            try:
                existing = await self.memory.get_facts(user_id)
                new_facts = await extract_facts(self.llm, self.settings.summary_model, user_name, existing, messages)
                await self.memory.save_facts(user_id, new_facts)
                synced += 1
                await ctx.send(f"✅ **{user_name}**: {len(new_facts)} facts")
            except Exception:
                log.exception("syncfacts_user_failed", user_id=user_id)
                errors += 1

        summary = f"🏁 Sync completo: **{synced}** usuarios procesados"
        if errors:
            summary += f", **{errors}** errores"
        await ctx.send(summary)

    @commands.command(name="setup")
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def setup(self, ctx: commands.Context):
        """Crea canales de sistema (facts + reminders) con formato cyberpunk."""
        if not ctx.guild:
            await ctx.send(get_error_response(ErrorType.GENERIC))
            return

        # Check if already set up
        config = await self.memory.get_guild_config(str(ctx.guild.id))
        if config and config["setup_complete"]:
            await ctx.send("Ya tengo mis canales montados, no seas redundante. Revisa la categoria **INSULT SYSTEMS**.")
            return

        try:
            await setup_guild(ctx.guild, self.memory)
            await ctx.send(
                "```\n"
                "░▒▓ SETUP COMPLETE ▓▒░\n"
                "║ category: INSULT SYSTEMS\n"
                "║ #insult-facts: online\n"
                "║ #insult-reminders: online\n"
                "╚════════════════════════════╝\n"
                "```\n"
                "Listo. Los canales son read-only — solo yo escribo ahi."
            )
        except (PermissionError, discord.Forbidden):
            await ctx.send("No tengo permiso de **Manage Channels**. Daselo al bot y vuelve a intentar.")
        except Exception:
            log.exception("setup_failed", guild_id=str(ctx.guild.id))
            await ctx.send(get_error_response(ErrorType.GENERIC))
