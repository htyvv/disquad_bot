import discord
from discord.ext import commands
from discord import ui
import datetime

class MVPVoteView(ui.View):
    def __init__(self, bot, schedule_id, participants, voter_team, max_votes, can_vote_own_team):
        super().__init__(timeout=None)
        self.bot = bot
        self.schedule_id = schedule_id
        self.participants = participants
        self.voter_team = voter_team
        self.max_votes = max_votes
        self.can_vote_own_team = can_vote_own_team
        self._create_buttons()
        
    def _create_buttons(self):
        # 참가자들을 팀 별로 분리
        team_a = [p for p in self.participants if p[2] == 1]
        team_b = [p for p in self.participants if p[2] == 2]
        
        # 팀 1(A) 버튼 추가
        if self.can_vote_own_team or self.voter_team != 1:
            for participant in team_a:
                button = ui.Button(label=participant[1], custom_id=f"mvp_vote:{participant[0]}", style=discord.ButtonStyle.green)
                button.callback = self.vote_callback
                self.add_item(button)
                
        # 팀 2(B) 버튼 추가
        if self.can_vote_own_team or self.voter_team != 2:
            for participant in team_b:
                button = ui.Button(label=participant[1], custom_id=f"mvp_vote:{participant[0]}", style=discord.ButtonStyle.red)
                button.callback = self.vote_callback
                self.add_item(button)
    
    async def vote_callback(self, interaction: discord.Interaction):
        voted_for_id = interaction.data["custom_id"].split(":")[1]
        voter_id = str(interaction.user.id)
        
        # 이미 투표한 횟수 확인
        used_votes = await self.bot.database.check_user_voted(self.schedule_id, voter_id)
        
        if used_votes >= self.max_votes:
            await interaction.response.send_message("❌ 모든 투표권을 사용했습니다.", ephemeral=True)
            return
        
        # 투표 기록
        await self.bot.database.record_mvp_vote(self.schedule_id, voter_id, voted_for_id)
        
        # 남은 투표권 계산
        remaining_votes = self.max_votes - used_votes - 1
        
        await interaction.response.send_message(
            f"✅ 투표가 완료되었습니다. 남은 투표권: {remaining_votes}표", 
            ephemeral=True
        )
        
        # 모든 투표권을 사용했으면 뷰 비활성화
        if remaining_votes <= 0:
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)


class MVPManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="mvp투표",
        description="현재 경기의 MVP를 투표합니다. 옵션을 통해 투표 방식을 설정할 수 있습니다."
    )
    async def start_mvp_vote(self, ctx: commands.Context, 
                            이긴팀_투표수: int = 3, 
                            진팀_투표수: int = 1,
                            자기팀_투표가능: bool = True):
        # 현재 확정된 가장 최근 일정 조회
        schedule = await self.bot.database.get_confirmed_schedule()
        
        if not schedule:
            await ctx.send("❌ 현재 확정된 내전 일정이 없습니다.", ephemeral=True)
            return
        
        schedule_id, schedule_date = schedule
        
        # 해당 일정의 경기 결과 확인
        match_result = await self.bot.database.get_match_result(schedule_id)
        if not match_result:
            await ctx.send("❌ 아직 경기 결과가 기록되지 않았습니다. 먼저 경기 결과를 기록해주세요.", ephemeral=True)
            return
        
        # MVP 투표 설정 저장
        await self.bot.database.create_mvp_vote(schedule_id, 이긴팀_투표수, 진팀_투표수, 자기팀_투표가능)
        
        # 임베드 메시지로 MVP 투표 안내
        embed = discord.Embed(
            title=f"🏆 {schedule_date} 내전 MVP 투표",
            description="아래 버튼을 눌러 MVP에 투표해주세요.",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="투표 방식",
            value=f"- 이긴 팀: {이긴팀_투표수}표\n- 진 팀: {진팀_투표수}표\n- 자기 팀 투표: {'가능' if 자기팀_투표가능 else '불가능'}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # 참가자 목록 조회
        participants = await self.bot.database.get_participants(schedule_id)
        
        # 각 참가자에게 투표 안내 DM 발송
        for participant in participants:
            user_id, user_name, team = participant
            
            # 사용자 객체 가져오기
            user = self.bot.get_user(int(user_id))
            if not user:
                continue
            
            # 팀에 따라 투표권 수 결정
            winning_team = match_result[0]
            max_votes = 이긴팀_투표수 if team == winning_team else 진팀_투표수
            
            dm_embed = discord.Embed(
                title=f"🏆 {schedule_date} 내전 MVP 투표",
                description=f"아래 버튼을 눌러 MVP에 투표해주세요. (총 {max_votes}표)",
                color=discord.Color.gold()
            )
            
            # 투표 UI 생성
            view = MVPVoteView(
                self.bot,
                schedule_id,
                participants,
                team,
                max_votes,
                자기팀_투표가능
            )
            
            try:
                await user.send(embed=dm_embed, view=view)
            except:
                # DM을 보낼 수 없는 경우 처리
                pass
    
    @commands.hybrid_command(
        name="mvp결과",
        description="현재 경기의 MVP 투표 결과를 확인합니다."
    )
    async def show_mvp_results(self, ctx: commands.Context):
        # 현재 확정된 가장 최근 일정 조회
        schedule = await self.bot.database.get_confirmed_schedule()
        
        if not schedule:
            await ctx.send("❌ 현재 확정된 내전 일정이 없습니다.", ephemeral=True)
            return
        
        schedule_id, schedule_date = schedule
        
        # MVP 투표 결과 조회
        votes = await self.bot.database.get_mvp_votes(schedule_id)
        
        if not votes:
            await ctx.send("❌ 아직 MVP 투표 결과가 없습니다.", ephemeral=True)
            return
        
        # 참가자 정보 매핑
        participants = await self.bot.database.get_participants(schedule_id)
        participant_map = {p[0]: p[1] for p in participants}
        
        # 임베드 메시지로 MVP 투표 결과 표시
        embed = discord.Embed(
            title=f"🏆 {schedule_date} 내전 MVP 투표 결과",
            color=discord.Color.gold()
        )
        
        for vote in votes:
            voted_for_id, total_votes = vote
            user_name = participant_map.get(voted_for_id, "알 수 없음")
            embed.add_field(
                name=user_name,
                value=f"{total_votes}표",
                inline=True
            )
        
        # MVP 결정 (가장 많은 표를 받은 사람)
        mvp_id, mvp_votes = votes[0]
        mvp_name = participant_map.get(mvp_id, "알 수 없음")
        
        embed.description = f"🎉 MVP: **{mvp_name}** ({mvp_votes}표)"
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(
        name="오늘의mvp",
        description="오늘 진행된 모든 경기의 MVP 중에서 가장 많은 표를 받은 플레이어를 선정합니다."
    )
    async def today_mvp(self, ctx: commands.Context):
        # 오늘 날짜 가져오기
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 오늘의 MVP 조회
        mvp = await self.bot.database.get_today_mvp(today)
        
        if not mvp:
            await ctx.send("❌ 오늘 진행된 경기의 MVP 투표 결과가 없습니다.", ephemeral=True)
            return
        
        mvp_id, mvp_name, total_votes = mvp
        
        # MVP 수상 기록
        await self.bot.database.record_mvp_award(today, mvp_id, mvp_name, total_votes)
        
        # 임베드 메시지로 오늘의 MVP 발표
        embed = discord.Embed(
            title=f"🏆 {today} 오늘의 MVP",
            description=f"축하합니다! 오늘의 MVP는 **{mvp_name}**님 입니다! ({total_votes}표)",
            color=discord.Color.gold()
        )
        
        # MVP 축하 이미지 추가 (옵션)
        # embed.set_thumbnail(url="https://media.discordapp.net/attachments/1076127927352156171/1076127981714477066/mvp_trophy.png")
        
        await ctx.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(MVPManagement(bot))