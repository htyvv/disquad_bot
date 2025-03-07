import discord
from discord.ext import commands
import datetime
import matplotlib.pyplot as plt
import io, base64
import matplotlib.font_manager as fm
import seaborn as sns

class ScheduleVoting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}  # 활성화된 투표 메시지 추적

    @commands.hybrid_command(
        name="내전일정생성", 
        description="투표할 날짜들을 쉼표로 구분해 입력합니다. Ex) `/내전일정생성 2025-03-05, 2025-03-06, 2025-03-07`"
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
        
        # 기존 "voting" 상태의 일정 확인
        existing_schedules = await self.bot.database.get_voting_schedules()
        if existing_schedules:
            await ctx.send("⚠️ 기존의 투표 일정이 취소되고 새로운 일정이 생성됩니다.", ephemeral=True)
            for schedule in existing_schedules:
                await self.bot.database.update_schedule_status(schedule[0], 'abandoned')
        
        # 안내 메시지 생성
        embed = discord.Embed(
            title="📅 롤 내전 일정 투표",
            description="아래 버튼을 눌러 참여 가능한 날짜에 투표해주세요!",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="투표 가능 날짜", value="\n".join([f"📌 **{date}**" for date in valid_dates]), inline=False)
        embed.set_footer(text="투표는 중복 선택 가능합니다. 가장 많은 표를 받은 날짜가 선정됩니다.")
        
        # 버튼 생성
        view = ScheduleVoteView(valid_dates, self.bot)
        
        await ctx.send(embed=embed, view=view)
        
        # 데이터베이스에 일정 후보 저장
        for date in valid_dates:
            await self.bot.database.insert_schedule(date)
            
    @commands.hybrid_command(
    name="투표현황", 
    description="현재 진행 중인 투표의 현황을 시각화하여 보여줍니다."
    )
    async def show_vote_status(self, ctx: commands.Context):
        # 현재 진행 중인 투표 일정 조회
        results = await self.bot.database.get_voting_schedules()
        
        if not results:
            await ctx.send("❌ 현재 진행 중인 투표가 없습니다.", ephemeral=True)
            return
        
        # 각 일정에 대한 투표 수 집계 및 참가자 목록
        vote_counts = {}
        participant_names = {}
        
        for schedule in results:
            schedule_id = schedule[0]
            schedule_date = schedule[1]
            vote_count = await self.bot.database.get_vote_count(schedule_id)
            participants = await self.bot.database.get_voters(schedule_id)  # 참가자 목록 조회
            
            vote_counts[schedule_date] = vote_count[0] if vote_count else 0
            participant_names[schedule_date] = [voter[0] for voter in participants]  # 참가자 이름 저장
        
        # 바 차트를 내림차순으로 정렬
        sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_dates, sorted_counts = zip(*sorted_votes)

        font_path = "C:\\Windows\\Fonts\\malgun.ttf"
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rc('font', family=font_name)

        # Seaborn 스타일 설정
        sns.set_theme(style="whitegrid")

        # 차트 생성
        plt.figure(figsize=(10, 6))
        sns.barplot(x=list(sorted_counts), y=list(sorted_dates), palette="Blues_d")
        # plt.xlabel('투표 수')
        plt.xlabel('N')
        # plt.title('현재 투표 현황')
        plt.title('Total Voting Count')
        
        # 차트를 이미지로 저장
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        # 이미지를 Discord에 전송
        buf.seek(0)  # 버퍼를 처음으로 되돌림
        file = discord.File(buf, filename="vote_status.png")
        
        # 참가자 목록을 문자열로 변환
        participant_info = "\n".join(
            [f"📌 **{date}** : {vote_counts[date]}표 (참가자: {', '.join(participant_names[date]) if participant_names[date] else 'X'})" for date in sorted_dates]
        )

        # 차트를 Discord에 전송
        embed = discord.Embed(
            title="📊 현재 투표 현황",
            description="각 날짜에 대한 투표 수와 참가자 목록입니다.",
            color=discord.Color.blue()
        )
        embed.add_field(name="투표 항목별 참가자", value=participant_info, inline=False)
        
        await ctx.send(embed=embed, file=file)

    @commands.hybrid_command(
        name="투표마감", 
        description="롤 내전 날짜 투표를 마감하고 결과를 발표합니다. 예를 들어, `/투표마감`을 입력하면 가장 많은 표를 받은 날짜가 내전 일정으로 확정됩니다."
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
            value="참가를 원하시는 분들은 **/참가** 를 입력해주세요!",
            inline=False
        )
        
        # 참가 신청 버튼 추가
        # view = RegisterView(winner_id, winner_date, self.bot)
        
        await ctx.send(embed=embed)
        # await ctx.send(embed=embed, view=view)

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

# # 내전 참가 신청 버튼 뷰
# class RegisterView(discord.ui.View):
#     def __init__(self, schedule_id, date, bot):
#         super().__init__(timeout=None)
#         self.schedule_id = schedule_id
#         self.date = date
#         self.bot = bot
        
#         # 참가 신청/취소 버튼 추가
#         self.add_item(discord.ui.Button(
#             label="참가",
#             style=discord.ButtonStyle.success,
#             custom_id=f"register_{schedule_id}"
#         ))
#         self.add_item(discord.ui.Button(
#             label="불참",
#             style=discord.ButtonStyle.danger,
#             custom_id=f"unregister_{schedule_id}"
#         ))

async def setup(bot) -> None:
    await bot.add_cog(ScheduleVoting(bot))