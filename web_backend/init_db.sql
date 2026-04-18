-- 创建 user_profile 表（Django 用户认证表）
CREATE TABLE IF NOT EXISTS user_profile (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    email VARCHAR(254) DEFAULT '',
    user_cate SMALLINT DEFAULT 1 COMMENT '0 女频，1 男频，2 出版',
    avatar VARCHAR(255) DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login DATETIME DEFAULT NULL,
    INDEX idx_username (username),
    INDEX idx_cate (user_cate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表';

-- 确保 novel_info 表有 index 主键（如果没有）
ALTER TABLE novel_info 
MODIFY COLUMN index INT AUTO_INCREMENT PRIMARY KEY;

-- 检查 user_behavior 表结构
ALTER TABLE user_behavior
MODIFY COLUMN read_time SMALLINT NOT NULL;

-- 添加必要的索引
ALTER TABLE user_behavior 
ADD INDEX idx_user_novel (user_id, novel_id);
