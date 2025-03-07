CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 내전 일정 테이블
CREATE TABLE IF NOT EXISTS `schedules` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `date` TEXT,
  `time` TEXT,
  `status` TEXT DEFAULT 'voting',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 일정 투표 테이블
CREATE TABLE IF NOT EXISTS `schedule_votes` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `schedule_id` INTEGER,
  `user_id` TEXT,
  `user_name` TEXT,
  FOREIGN KEY (`schedule_id`) REFERENCES `schedules`(`id`),
  UNIQUE(`schedule_id`, `user_id`)
);

-- 참가자 테이블
CREATE TABLE IF NOT EXISTS `participants` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `schedule_id` INTEGER,
  `user_id` TEXT,
  `user_name` TEXT,
  `team` INTEGER DEFAULT NULL,
  FOREIGN KEY (`schedule_id`) REFERENCES `schedules`(`id`),
  UNIQUE(`schedule_id`, `user_id`)
);

-- 경기 결과 테이블
CREATE TABLE IF NOT EXISTS `match_results` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `schedule_id` INTEGER,
  `winning_team` INTEGER,
  `match_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`schedule_id`) REFERENCES `schedules`(`id`)
);

-- 플레이어 전적 테이블
CREATE TABLE IF NOT EXISTS `player_stats` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `user_id` TEXT,
  `user_name` TEXT,
  `wins` INTEGER DEFAULT 0,
  `losses` INTEGER DEFAULT 0,
  UNIQUE(`user_id`)
);

-- MVP 투표 설정 테이블
CREATE TABLE IF NOT EXISTS `mvp_vote_settings` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `schedule_id` INTEGER,
  `winning_team_votes` INTEGER DEFAULT 2,
  `losing_team_votes` INTEGER DEFAULT 1,
  `can_vote_own_team` BOOLEAN DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`schedule_id`) REFERENCES `schedules`(`id`)
);

-- MVP 투표 테이블
CREATE TABLE IF NOT EXISTS `mvp_votes` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `schedule_id` INTEGER,
  `voter_id` TEXT,
  `voted_for_id` TEXT,
  `vote_count` INTEGER DEFAULT 1,
  `vote_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`schedule_id`) REFERENCES `schedules`(`id`)
);

-- MVP 수상 기록 테이블
CREATE TABLE IF NOT EXISTS `mvp_awards` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `date` TEXT,
  `user_id` TEXT,
  `user_name` TEXT,
  `total_votes` INTEGER,
  `award_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);