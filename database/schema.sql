-- Reference MySQL 8 schema for Insurance Assistant.
-- The recommended setup command is: python -m flask --app app init-db
-- SQLAlchemy creates these same tables automatically.

CREATE TABLE IF NOT EXISTS `user` (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS insurance_profile (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  current_step INT NOT NULL DEFAULT 0,
  age INT NULL,
  insurance_type VARCHAR(60) NULL,
  budget_period VARCHAR(20) NULL,
  budget_amount DECIMAL(14,2) NULL,
  coverage_amount VARCHAR(100) NULL,
  has_existing_policy VARCHAR(10) NULL,
  completed_at DATETIME NULL,
  updated_at DATETIME NULL,
  CONSTRAINT fk_insurance_profile_user FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS faq (
  id INT AUTO_INCREMENT PRIMARY KEY,
  question VARCHAR(300) NOT NULL,
  answer TEXT NOT NULL,
  keywords VARCHAR(500) NULL,
  category VARCHAR(100) NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NULL,
  INDEX idx_faq_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_message (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  conversation_id VARCHAR(36) NOT NULL,
  role VARCHAR(20) NOT NULL,
  message TEXT NOT NULL,
  source VARCHAR(30) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_chat_user (user_id),
  INDEX idx_chat_conversation (conversation_id),
  CONSTRAINT fk_chat_message_user FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
