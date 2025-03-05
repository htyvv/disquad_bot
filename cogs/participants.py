import discord
from discord.ext import commands
import random

class ParticipantManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.team_a_name = "🟢 Team 1"
        self.team_b_name = "🔴 Team 2"

    async def assign_teams_and_create_embed(self, schedule_id, user_list, title):
        # 랜덤 팀 배정
        random.shuffle(user_list)
        team_a = user_list[:5]
        team_b = user_list[5:]

        # 팀 정보 데이터베이스에 저장
        await self.bot.database.assign_teams(schedule_id, team_a, team_b)

        # 임베드 메시지로 팀 배정 결과 표시
        embed = discord.Embed(
            title=title,
            color=discord.Color.green()
        )

        embed.add_field(
            name=self.team_a_name, 
            value="\n".join(user[1] for user in team_a),
            inline=True
        )
        embed.add_field(
            name=self.team_b_name, 
            value="\n".join(user[1] for user in team_b),
            inline=True
        )

        return embed

    @commands.hybrid_command(
        name="참가", 
        description="롤 내전 참가 신청을 합니다"
    )
    async def register_participant(self, ctx: commands.Context):
        # 현재 확정된 가장 최근 일정 조회
        schedule = await self.bot.database.get_confirmed_schedule()

        if not schedule:
            await ctx.send("❌ 현재 확정된 내전 일정이 없습니다.", ephemeral=True)
            return

        schedule_id, schedule_date = schedule

        user_id = str(ctx.author.id)
        user_name = ctx.author.display_name

        # 이미 참가 신청했는지 확인
        existing_participant = await self.bot.database.check_participant(schedule_id, user_id)
        if existing_participant:
            embed = discord.Embed(
                title="⚠️ 내전 참가 신청 오류",
                description=f"**{user_name}**님, {schedule_date} 이미 참가 신청되어 있습니다.",
                color=discord.Color.yellow()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        # 참가자 제한 확인 (10명)
        participant_count = await self.bot.database.get_participant_count(schedule_id)
        if participant_count[0] >= 10:
            await ctx.send("❌ 참가 인원(10명)이 모두 찼습니다.", ephemeral=True)
            return

        # 참가자 등록
        await self.bot.database.register_participant(schedule_id, user_id, user_name)

        # 임베드 메시지로 참가 확인
        embed = discord.Embed(
            title="✅ 내전 참가 신청 완료",
            description=f"**{user_name}**님, {schedule_date} 내전 참가 신청이 완료되었습니다!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="참가취소", 
        description="롤 내전 참가 신청을 취소합니다"
    )
    async def unregister_participant(self, ctx: commands.Context):
        # 현재 확정된 가장 최근 일정 조회
        schedule = await self.bot.database.get_confirmed_schedule()

        if not schedule:
            await ctx.send("❌ 현재 확정된 내전 일정이 없습니다.", ephemeral=True)
            return

        schedule_id, schedule_date = schedule

        user_id = str(ctx.author.id)

        # 참가 신청 여부 확인
        existing_participant = await self.bot.database.check_participant(schedule_id, user_id)
        if not existing_participant:
            await ctx.send("❌ 참가 신청 내역이 없습니다.", ephemeral=True)
            return

        # 참가 취소 처리
        await self.bot.database.unregister_participant(schedule_id, user_id)

        # 임베드 메시지로 취소 확인
        embed = discord.Embed(
            title="🚫 내전 참가 취소 완료",
            description=f"**{ctx.author.display_name}**님, {schedule_date} 내전 참가가 취소되었습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="참가자목록", 
        description="현재 내전 참가자 목록을 확인합니다"
    )
    async def list_participants(self, ctx: commands.Context):
        # 현재 확정된 가장 최근 일정 조회
        schedule = await self.bot.database.get_confirmed_schedule()

        if not schedule:
            await ctx.send("❌ 현재 확정된 내전 일정이 없습니다.", ephemeral=True)
            return

        schedule_id, schedule_date = schedule

        # 참가자 목록 조회
        participants = await self.bot.database.get_participants(schedule_id)

        if not participants:
            await ctx.send("🕹️ 현재 참가자가 없습니다.", ephemeral=True)
            return

        # 임베드 메시지로 참가자 목록 표시
        embed = discord.Embed(
            title=f"📋 {schedule_date} 내전 참가자 목록",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🔵 참가자 목록 (총 {}명)".format(len(participants)), 
            value="전체 참가자: " + ", ".join(p[1] for p in participants),
            inline=False
        )

        # 팀 배정 상태 표시
        team_a = [p[1] for p in participants if p[2] == 1]
        team_b = [p[1] for p in participants if p[2] == 2]
        no_team = [p[1] for p in participants if p[2] is None]

        if team_a or team_b:
            embed.add_field(
                name=self.team_a_name, 
                value="\n".join(team_a) if team_a else "아직 배정 안됨",
                inline=True
            )
            embed.add_field(
                name=self.team_b_name, 
                value="\n".join(team_b) if team_b else "아직 배정 안됨",
                inline=True
            )
        
        if no_team:
            embed.add_field(
                name="⚪ 미배정 인원", 
                value="\n".join(no_team),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="팀배정", 
        description="참가자들을 랜덤으로 팀 배정합니다"
    )
    async def assign_teams(self, ctx: commands.Context):
        # 현재 확정된 가장 최근 일정 조회
        schedule = await self.bot.database.get_confirmed_schedule()

        if not schedule:
            await ctx.send("❌ 현재 확정된 내전 일정이 없습니다.", ephemeral=True)
            return

        schedule_id, schedule_date = schedule

        # 참가자 조회
        participants = await self.bot.database.get_participants(schedule_id)

        if len(participants) < 10:
            await ctx.send(f"❌ 팀 배정을 위해서는 10명의 참가자가 필요합니다. (현재 {len(participants)}명)", ephemeral=True)
            return

        # 팀 배정 및 임베드 생성
        embed = await self.assign_teams_and_create_embed(schedule_id, participants, f"🎲 {schedule_date} 내전 팀 배정 결과")
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="즉흥팀배정",
        description="현재 음성 채널에 있는 사용자들을 랜덤으로 두 팀으로 배정합니다"
    )
    async def spontaneous_team_assignment(self, ctx: commands.Context):
        # 사용자가 음성 채널에 있는지 확인
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ 음성 채널에 참여하고 있지 않습니다.", ephemeral=True)
            return

        # 음성 채널의 모든 사용자 가져오기
        voice_channel = ctx.author.voice.channel
        members = voice_channel.members

        if len(members) < 10:
            await ctx.send(f"❌ 팀 배정을 위해서는 10명의 사용자가 필요합니다. (현재 {len(members)}명)", ephemeral=True)
            return

        # 사용자 ID와 이름 목록 생성
        user_list = [(member.id, member.display_name) for member in members]

        # 참가자 등록
        schedule_id = 0  # 즉흥적인 경우이므로 임시로 0을 사용
        for user_id, user_name in user_list:
            await self.bot.database.register_participant(schedule_id, user_id, user_name)

        # 팀 배정 및 임베드 생성
        embed = await self.assign_teams_and_create_embed(schedule_id, user_list, "🎲 즉흥 팀 배정 결과")
        await ctx.send(embed=embed)
        
    # cogs/participants.py에 추가

    @commands.hybrid_command(
        name="경기결과",
        description="경기가 끝난 후 승리한 팀을 입력하여 결과를 저장합니다."
    )
    async def record_match_result(self, ctx: commands.Context, winning_team: str):
        # 현재 확정된 가장 최근 일정 조회
        schedule = await self.bot.database.get_confirmed_schedule()

        if not schedule:
            await ctx.send("❌ 현재 확정된 내전 일정이 없습니다.", ephemeral=True)
            return

        schedule_id, _ = schedule

        # 승리한 팀 정보 저장
        if winning_team not in ["1", "2"]:
            await ctx.send("❌ 유효하지 않은 팀 번호입니다. 1 또는 2를 입력하세요.", ephemeral=True)
            return

        await self.bot.database.record_match_result(schedule_id, int(winning_team))

        # 경기 결과 저장 후 다음 일정 준비
        await self.bot.database.update_schedule_status(schedule_id, 'completed')
        await ctx.send("✅ 경기 결과가 저장되었습니다. 다음 일정을 준비할 수 있습니다.", ephemeral=True)
        
    @commands.hybrid_command(
        name="승률",
        description="플레이어의 승률을 출력합니다. 예제: /승률 user_name:준병이어머, /승률 team:1, /승률"
    )
    async def show_win_rate(self, ctx: commands.Context, user_name: str = None, team: str = None):
        if user_name:
            # 특정 사용자의 승률 조회
            stats = await self.bot.database.get_player_stats(user_name=user_name)
            if not stats:
                await ctx.send(f"❌ {user_name}님의 전적이 없습니다.", ephemeral=True)
                return
            wins, losses = stats[0][3], stats[0][4]
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
            await ctx.send(f"**{user_name}**님의 승률: {win_rate:.2f}% (승리: {wins}, 패배: {losses})", ephemeral=True)
        elif team:
            # 특정 팀의 승률 요약
            participants = await self.bot.database.get_participants_by_team(team)
            if not participants:
                await ctx.send(f"❌ {team} 팀의 전적이 없습니다.", ephemeral=True)
                return
            summary = []
            for participant in participants:
                user_name, wins, losses = participant[1], participant[3], participant[4]
                win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
                summary.append(f"{user_name}: {win_rate:.2f}% (승리: {wins}, 패배: {losses})")
            await ctx.send("\n".join(summary), ephemeral=True)
        else:
            # 모든 참가자의 승률 출력
            participants = await self.bot.database.get_all_participants_stats()
            if not participants:
                await ctx.send("❌ 참가자 전적이 없습니다.", ephemeral=True)
                return
            summary = []
            for participant in participants:
                user_name, wins, losses = participant[1], participant[3], participant[4]
                win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
                summary.append(f"{user_name}: {win_rate:.2f}% (승리: {wins}, 패배: {losses})")
            await ctx.send("\n".join(summary), ephemeral=True)    
    
        
async def setup(bot) -> None:
    await bot.add_cog(ParticipantManagement(bot))