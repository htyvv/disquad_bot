"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.2.0
"""

import aiosqlite


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        This function will add a warn to the database.

        :param user_id: The ID of the user that should be warned.
        :param reason: The reason why the user should be warned.
        """
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await self.connection.commit()
            return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        """
        This function will remove a warn from the database.

        :param warn_id: The ID of the warn.
        :param user_id: The ID of the user that was warned.
        :param server_id: The ID of the server where the user has been warned
        """
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        """
        This function will get all the warnings of a user.

        :param user_id: The ID of the user that should be checked.
        :param server_id: The ID of the server that should be checked.
        :return: A list of all the warnings of the user.
        """
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

    async def insert_schedule(self, date, time='20:00', status='voting'):
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                'INSERT INTO schedules (date, time, status) VALUES (?, ?, ?)',
                (date, time, status)
            )
            await self.connection.commit()

    async def get_voting_schedules(self):
        async with self.connection.cursor() as cursor:
            await cursor.execute('''
                SELECT s.id, s.date, COUNT(sv.id) as vote_count
                FROM schedules s
                LEFT JOIN schedule_votes sv ON s.id = sv.schedule_id
                WHERE s.status = 'voting'
                GROUP BY s.id
                ORDER BY vote_count DESC, s.date ASC
            ''')
            return await cursor.fetchall()

    async def update_schedule_status(self, schedule_id, status):
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                'UPDATE schedules SET status = ? WHERE id = ?',
                (status, schedule_id)
            )
            await self.connection.commit()

    async def get_voters(self, schedule_id):
        async with self.connection.cursor() as cursor:
            await cursor.execute('''
                SELECT user_name FROM schedule_votes
                WHERE schedule_id = ?
            ''', (schedule_id,))
            return await cursor.fetchall()

    async def insert_vote(self, schedule_id, user_id, user_name):
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                'INSERT INTO schedule_votes (schedule_id, user_id, user_name) VALUES (?, ?, ?)',
                (schedule_id, user_id, user_name)
            )
            await self.connection.commit()

    async def delete_vote(self, schedule_id, user_id):
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                'DELETE FROM schedule_votes WHERE schedule_id = ? AND user_id = ?',
                (schedule_id, user_id)
            )
            await self.connection.commit()

    async def get_vote_count(self, schedule_id, user_id=None):
        async with self.connection.cursor() as cursor:
            if user_id:
                # 특정 사용자의 투표 수 조회
                await cursor.execute('''
                    SELECT COUNT(*) FROM schedule_votes WHERE schedule_id = ? AND user_id = ?
                ''', (schedule_id, user_id))
            else:
                # 전체 투표 수 조회
                await cursor.execute('''
                    SELECT COUNT(*) FROM schedule_votes WHERE schedule_id = ?
                ''', (schedule_id,))
            return await cursor.fetchone()
