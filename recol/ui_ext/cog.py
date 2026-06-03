from typing import TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands
from ballsdex.core.utils.transformers import (
    BallEnabledTransform,
)
from ballsdex.core.utils.utils import inventory_privacy, is_staff
from bd_models.models import BallInstance, Player, Special
from settings.models import settings
from ..models import recol_setting

from ballsdex.core.bot import BallsDexBot
if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot
from django.db.models import Count, Exists, F, OuterRef, Q



class Collection(discord.ui.LayoutView):
    def __init__(self, user, totals, specials, specials2):
        super().__init__()
        self.user = user
        self.totals = totals
        self.total_specials = specials
        self.specials = specials2
        self.create()
    def create(self):
        container1 = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(content=f"# {self.user.mention}'s collection:\nProtip: check me out on github! (@cewlgruyere)"),
                accessory=discord.ui.Thumbnail(
                    media=self.user.display_avatar.url,
                ),
            ),

            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay(content=f"## Total amount of balls:\n{self.totals}"),
            discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"## Total special amount:\n{self.total_specials}"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay(content=f"## Specials:\n{self.specials}"),
        )
        self.add_item(container1)


class recol(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    async def collection(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        user: discord.User | None = None,
        countryball: BallEnabledTransform | None = None,
        ephemeral: bool = False,
    ):
        """
        Show the collection of a specific countryball.

        Parameters
        ----------
        countryball: Ball
            The countryball you want to see the collection of
        user: discord.User
            The user you want to view the collection of.
        ephemeral: bool
            Whether or not to send the command ephemerally.
        """
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        if user is not None:
            try:
                player = await Player.objects.aget(discord_id=user.id)
            except Player.DoesNotExist:
                await interaction.followup.send(
                    f"{user.name} doesn't have any {settings.plural_collectible_name} yet."
                )
                return
            staff = await is_staff(interaction)
            if user.id in self.bot.blacklist and not staff:
                await interaction.followup.send("You cannot view the completion of a blacklisted user.", ephemeral=True)
                return

            interaction_player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)

            blocked = await player.is_blocked(interaction_player)
            if blocked and not staff:
                await interaction.followup.send(
                    "You cannot view the completion of a user that has blocked you.", ephemeral=True
                )
                return

            if await inventory_privacy(self.bot, interaction, player, user) is False:
                return
        user = interaction.user if not user else user
        player, _ = await Player.objects.aget_or_create(discord_id=user.id)


        query = (
            BallInstance.objects.filter(player=player)
            .values("player_id")
            .annotate(
                total=Count("id"),
                traded=Count("id", filter=Q(trade_player_id__isnull=False)),
                specials=Count(
                    "id",
                    filter=Q(special_id__isnull=False)
                    & ~Exists(Special.objects.filter(hidden=True, id=OuterRef("special_id"))),
                ),
            )
        )
        specials = (
            BallInstance.objects.filter(player=player)
            .exclude(special=None)
            .exclude(special__hidden=True)
            .values("special__name")
            .annotate(count=Count("special__name"))
            .order_by("-count")
        )
        if countryball:
            query = query.filter(ball=countryball)
            specials = specials.filter(ball=countryball)

        try:
            counts = await query.aget()
        except BallInstance.DoesNotExist:
            if countryball:
                await interaction.followup.send(
                    f"You don't have any {countryball.country} {settings.plural_collectible_name} yet."
                )
            else:
                await interaction.followup.send(f"You don't have any {settings.plural_collectible_name} yet.")
            return
        all_specials = Special.objects.filter(hidden=False)
        special_emojis = {x.name: x.emoji async for x in all_specials}

        desc = (
            f"**Total**: {counts['total']:,} ({counts['total'] - counts['traded']:,} caught, "
            f"{counts['traded']:,} received from trade)\n"
            f"**Total Specials**: {counts['specials']:,}\n\n"
        )
        if counts["specials"]:
            desc += "**Specials**:\n"
        async for special in specials:
            emoji = special_emojis.get(special["special__name"], "")
            desc += f"{emoji} {special['special__name']}: {special['count']:,}\n"

        embed = discord.Embed(
            title=f"Collection of {countryball.country}" if countryball else "Total Collection",
            description=desc,
            color=discord.Color.blurple(),
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        if countryball:
            file_location = countryball.wild_card.path
            file = discord.File(file_location, filename="countryball.png")
            embed.set_thumbnail(url="attachment://countryball.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)

    async def collection_v2(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        user: discord.User | None = None,
        countryball: BallEnabledTransform | None = None,
        ephemeral: bool = False,  
    ):
        """
        Show the collection of a specific countryball.

        Parameters
        ----------
        countryball: Ball
            The countryball you want to see the collection of
        user: discord.User
            The user you want to view the collection of.
        ephemeral: bool
            Whether or not to send the command ephemerally.
        """
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        if user is not None:
            try:
                player = await Player.objects.aget(discord_id=user.id)
            except Player.DoesNotExist:
                await interaction.followup.send(
                    f"{user.name} doesn't have any {settings.plural_collectible_name} yet."
                )
                return
            staff = await is_staff(interaction)
            if user.id in self.bot.blacklist and not staff:
                await interaction.followup.send("You cannot view the completion of a blacklisted user.", ephemeral=True)
                return

            interaction_player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)

            blocked = await player.is_blocked(interaction_player)
            if blocked and not staff:
                await interaction.followup.send(
                    "You cannot view the completion of a user that has blocked you.", ephemeral=True
                )
                return

            if await inventory_privacy(self.bot, interaction, player, user) is False:
                return
        user = interaction.user if not user else user
        player, _ = await Player.objects.aget_or_create(discord_id=user.id)


        query = (
            BallInstance.objects.filter(player=player)
            .values("player_id")
            .annotate(
                total=Count("id"),
                traded=Count("id", filter=Q(trade_player_id__isnull=False)),
                specials=Count(
                    "id",
                    filter=Q(special_id__isnull=False)
                    & ~Exists(Special.objects.filter(hidden=True, id=OuterRef("special_id"))),
                ),
            )
        )
        specials = (
            BallInstance.objects.filter(player=player)
            .exclude(special=None)
            .exclude(special__hidden=True)
            .values("special__name")
            .annotate(count=Count("special__name"))
            .order_by("-count")
        )
        if countryball:
            query = query.filter(ball=countryball)
            specials = specials.filter(ball=countryball)

        try:
            counts = await query.aget()
        except BallInstance.DoesNotExist:
            if countryball:
                await interaction.followup.send(
                    f"You don't have any {countryball.country} {settings.plural_collectible_name} yet."
                )
            else:
                await interaction.followup.send(f"You don't have any {settings.plural_collectible_name} yet.")
            return
        all_specials = Special.objects.filter(hidden=False)
        special_emojis = {x.name: x.emoji async for x in all_specials}

        desc = (
            f"**Total**: {counts['total']:,} ({counts['total'] - counts['traded']:,} caught, "
            f"{counts['traded']:,} received from trade)\n"
            f"**Total Specials**: {counts['specials']:,}\n\n"
        )
        total = f"**{counts['total']:,}** *({counts['total'] - counts['traded']:,} caught, {counts['traded']:,} received from trade)*"
        specials_1 = f"{counts['specials']:,}"
        special_text = ""
        async for special in specials:
            emoji = special_emojis.get(special["special__name"], "")
            special_text += f"{emoji} {special['special__name']}: {special['count']:,}\n"
        view = Collection(user, total, specials_1, special_text)
        await interaction.followup.send(view=view)



    async def cog_load(self):
        await self.bot.wait_until_ready()
        setting = await recol_setting.objects.afirst()
        group = self.bot.tree.get_command(settings.balls_slash_name)

        if group and isinstance(group, app_commands.Group):
            if setting.default_ui == True:
                group.remove_command("collection")
                group.add_command(app_commands.Command(
                    name="collection",
                    callback=self.collection,
                    description=f"Show your current completion of the {settings.bot_name}"
                ))
            else:
                group.remove_command("collection")
                group.add_command(app_commands.Command(
                    name="collection",
                    callback=self.collection_v2,
                    description=f"Show your current completion of the {settings.bot_name}"
                ))

        await self.bot.tree.sync()