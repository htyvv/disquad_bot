import discord
from discord.ext import commands
import datetime


class ScheduleVoting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}  # 활성화된 투표 메시지 추적

    @commands.hybrid_command(
        name="내전일정생성", 
        description="투표할 날짜들을 쉼표로 구분하여 입력 (예: 2025-03-05, 2025-03-06, 2025-03-07)"
    )
    async def create_schedule_poll(self, ctx: commands.Context, dates: str):
        # 입력된 날짜 처리
        dates = [date.strip().replace(" ", "") for date in dates.split(',')]
        
        # 날짜 형식 검증
        invalid_dates = []
        valid_dates = []
        for date in dates:
            try:
                datetime.datetime.strptime(date, '%Y-%m-%d')
                valid_dates.append(date)
            except ValueError:
                invalid_dates.append(date)
        
        if invalid_dates:
            await ctx.send(
                f"❌ 다음 날짜 형식이 올바르지 않습니다: {', '.join(invalid_dates)}\n"
                f"YYYY-MM-DD 형식으로 입력해주세요. (예: 2025-03-05)",
                ephemeral=True
            )
            return
        
        if not valid_dates:
            await ctx.send(
                "❌ 유효한 날짜가 없습니다. YYYY-MM-DD 형식으로 입력해주세요. (예: 2025-03-05)",
                ephemeral=True
            )
            return
        
        # 안내 메시지 생성
        embed = discord.Embed(
            title="📅 롤 내전 일정 투표",
            description="아래 버튼을 눌러 참여 가능한 날짜에 투표해주세요!",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="투표 가능 날짜", value="\n".join([f"📌 {date}" for date in valid_dates]), inline=False)
        embed.set_footer(text="투표는 중복 선택 가능합니다. 가장 많은 표를 받은 날짜가 선정됩니다.")
        
        # 버튼 생성
        view = ScheduleVoteView(valid_dates, self.bot)
        
        await ctx.send(embed=embed, view=view)
        
        # 데이터베이스에 일정 후보 저장
        for date in valid_dates:
            await self.bot.database.insert_schedule(date)

    @commands.hybrid_command(
        name="투표마감", 
        description="롤 내전 날짜 투표를 마감하고 결과를 발표합니다"
    )
    async def close_vote(self, ctx: commands.Context):
        # 투표 결과 조회
        results = await self.bot.database.get_voting_schedules()
        
        if not results:
            await ctx.send("❌ 현재 진행 중인 투표가 없습니다.", ephemeral=True)
            return
        
        # 가장 많은 표를 받은 날짜 선정
        winner_id, winner_date, vote_count = results[0]
        
        # 해당 일정 상태 업데이트
        await self.bot.database.update_schedule_status(winner_id, 'confirmed')
        
        # 다른 투표중인 일정들은 취소 처리
        for schedule in results[1:]:
            await self.bot.database.update_schedule_status(schedule[0], 'cancelled')
        
        # 투표한 사용자 목록 조회
        voters = await self.bot.database.get_voters(winner_id)
        voter_text = ', '.join(voter[0] for voter in voters) if voters else "없음"
        
        # 결과 발표 메시지
        embed = discord.Embed(
            title="🏆 롤 내전 일정 투표 결과",
            description=f"투표 결과 **{winner_date}**에 내전이 진행됩니다!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="📊 투표 수", value=f"{vote_count}표", inline=False)
        embed.add_field(name="👥 투표자 목록", value=voter_text, inline=False)
        embed.add_field(
            name="📣 참가 신청",
            value="참가를 원하시는 분들은 `/내전참가` 명령어로 참가 신청해주세요!",
            inline=False
        )
        
        # 참가 신청 버튼 추가
        view = RegisterView(winner_id, winner_date, self.bot)
        
        await ctx.send(embed=embed, view=view)

# 날짜 투표용 버튼 뷰
class ScheduleVoteView(discord.ui.View):
    def __init__(self, dates, bot):
        super().__init__(timeout=None)
        self.dates = dates
        self.bot = bot
        
        # 날짜마다 버튼 생성
        for date in dates:
            button = ScheduleVoteButton(date, self.bot)
            self.add_item(button)

# 날짜 투표 버튼
class ScheduleVoteButton(discord.ui.Button):
    def __init__(self, date, bot):
        super().__init__(
            label=date,
            style=discord.ButtonStyle.primary,
            custom_id=f"vote_{date}"
        )
        self.date = date
        self.bot = bot
    
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_name = interaction.user.display_name
        
        # 해당 날짜의 일정 ID 조회
        schedule = await self.bot.database.get_voting_schedules()
        schedule_id = next((s[0] for s in schedule if s[1] == self.date), None)
        
        if not schedule_id:
            await interaction.response.send_message("❌ 해당 날짜의 투표가 이미 마감되었습니다.", ephemeral=True)
            return
        
        # 이미 투표했는지 확인
        existing_vote = await self.bot.database.get_vote_count(schedule_id, user_id)
        
        if existing_vote and existing_vote[0] > 0:
            # 이미 투표한 경우 취소
            await self.bot.database.delete_vote(schedule_id, user_id)
            message = f"🗑️ {self.date} 날짜에 대한 투표를 취소했습니다."
        else:
            # 새로 투표
            await self.bot.database.insert_vote(schedule_id, user_id, user_name)
            message = f"✅ {self.date} 날짜에 투표했습니다!"
        
        # 현재 투표 수 조회
        vote_count = await self.bot.database.get_vote_count(schedule_id)
        
        await interaction.response.send_message(f"{message} \n(현재 {vote_count[0]}표)", ephemeral=True)

# 내전 참가 신청 버튼 뷰
class RegisterView(discord.ui.View):
    def __init__(self, schedule_id, date, bot):
        super().__init__(timeout=None)
        self.schedule_id = schedule_id
        self.date = date
        self.bot = bot
        
        # 참가 신청/취소 버튼 추가
        self.add_item(discord.ui.Button(
            label="참가 신청",
            style=discord.ButtonStyle.success,
            custom_id=f"register_{schedule_id}"
        ))
        self.add_item(discord.ui.Button(
            label="참가 취소",
            style=discord.ButtonStyle.danger,
            custom_id=f"unregister_{schedule_id}"
        ))

async def setup(bot) -> None:
    await bot.add_cog(ScheduleVoting(bot))