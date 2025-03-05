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