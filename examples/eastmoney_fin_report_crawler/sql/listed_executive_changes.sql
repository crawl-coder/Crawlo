CREATE TABLE `listed_executive_changes` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `pmid` CHAR(32) NOT NULL COMMENT '业务主键，MD5(changer|change_date|supervisor_name)，唯一索引',
  `change_date` DATETIME NOT NULL COMMENT '变动日期',
  `stock_code` VARCHAR(12) NOT NULL COMMENT '股票代码，如 000001.SZ',
  `stock_name` VARCHAR(64) NOT NULL COMMENT '股票名称',
  `changer` VARCHAR(100) NOT NULL COMMENT '变动人姓名',
  `change_shares` BIGINT DEFAULT NULL COMMENT '变动股数（正为增持，负为减持）',
  `average_trading_price` DECIMAL(20,4) DEFAULT NULL COMMENT '成交均价（元）',
  `change_amount` DECIMAL(24,4) DEFAULT NULL COMMENT '变动金额（元）',
  `change_reason` VARCHAR(255) DEFAULT NULL COMMENT '变动原因，如 竞价交易、大宗交易',
  `change_ratio` DECIMAL(8,4) DEFAULT NULL COMMENT '变动比例（%），如 0.0318 表示 3.18%',
  `shares_after_change` BIGINT DEFAULT NULL COMMENT '变动后持股数（股）',
  `share_type` VARCHAR(16) DEFAULT NULL COMMENT '持股种类，如 A股',
  `supervisor_name` VARCHAR(100) NOT NULL COMMENT '董监高人员姓名',
  `position` VARCHAR(225) DEFAULT NULL COMMENT '职务',
  `relationship_with_supervisor` VARCHAR(32) DEFAULT NULL COMMENT '变动人与董监高关系，如 本人、配偶、子女等',

  -- ========== 系统字段 ==========
  `created` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

  -- ========== 索引 ==========
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pmid` (`pmid`),
  INDEX `idx_stock_code` (`stock_code`),
  INDEX `idx_change_date` (`change_date`),
  INDEX `idx_changer` (`changer`),
  INDEX `idx_supervisor_name` (`supervisor_name`),
  INDEX `idx_updated` (`updated`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='上市公司-高管持股变动明细表';