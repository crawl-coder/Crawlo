CREATE TABLE `listed_senior_executives` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `pmid` CHAR(32) NOT NULL COMMENT '业务主键，MD5(stock_code + name)，唯一索引',
  `stock_code` VARCHAR(12) NOT NULL COMMENT '股票代码，如 000001.SZ',
  `stock_name` VARCHAR(64) NOT NULL COMMENT '股票名称',
  `name` VARCHAR(100) NOT NULL COMMENT '姓名',
  `gender` VARCHAR(8) DEFAULT NULL COMMENT '性别',
  `age` TINYINT UNSIGNED DEFAULT NULL COMMENT '年龄',
  `education` VARCHAR(32) DEFAULT NULL COMMENT '学历',
  `shareholding_num` BIGINT DEFAULT NULL COMMENT '持股数（股）',
  `salary` DECIMAL(24,4) DEFAULT NULL COMMENT '薪酬（元）',
  `position` VARCHAR(255) DEFAULT NULL COMMENT '职务，多个职务用逗号分隔',
  `tenure_start_date` DATE DEFAULT NULL COMMENT '任职开始日期',
  `tenure_end_date` DATE DEFAULT NULL COMMENT '任职结束日期',
  `introduction` TEXT DEFAULT NULL COMMENT '高管简介',

  -- ========== 系统字段 ==========
  `created` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

  -- ========== 索引 ==========
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pmid` (`pmid`),
  INDEX `idx_stock_code` (`stock_code`),
  INDEX `idx_name` (`name`),
  INDEX `idx_position` (`position`(32)),
  INDEX `idx_updated` (`updated`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='上市公司-高管信息表';