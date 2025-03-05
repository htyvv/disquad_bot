import discord
from discord.ext import commands

class HelpView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.current_page = 0

    @discord.ui.button(label="이전", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()  # 응답을 지연시킵니다.

    @discord.ui.button(label="다음", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()  # 응답을 지연시킵니다.

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="도움",
        description="사용 가능한 모든 명령어를 보여줍니다."
    )
    async def show_help(self, ctx: commands.Context):
        commands_per_embed = 15  # 임베드당 최대 명령어 수
        command_list = [cmd for cmd in self.bot.walk_commands() if any('가' <= char <= '힣' for char in cmd.name)]
        embeds = []

        for i in range(0, len(command_list), commands_per_embed):
            embed = discord.Embed(
                title="👶🏻 **도움말**",
                description="*사용 가능한 명령어 목록입니다.*",
                color=discord.Color.pink()
            )

            for command in command_list[i:i + commands_per_embed]:
                if command.description:
                    embed.add_field(
                        name=f"/{command.name}",
                        value=command.description,
                        inline=False
                    )

            embeds.append(embed)

        if embeds:
            view = HelpView(embeds)
            await ctx.send(embed=embeds[0], view=view)

async def setup(bot) -> None:
    await bot.add_cog(HelpCog(bot))