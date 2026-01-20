CREATE TABLE `listed_finance_and_taxation_report` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `pmid` VARCHAR(32) NOT NULL COMMENT 'md5(stock_code+report_date)',
  `stock_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
  `stock_name` VARCHAR(255) NOT NULL COMMENT '股票简称',
  `report_date` DATE NOT NULL COMMENT '报告日期',

  -- ========== 每股指标 ========== 
  `basic_eps` DECIMAL(15,4) DEFAULT NULL COMMENT '基本每股收益 (元)',
  `diluted_eps` DECIMAL(15,4) DEFAULT NULL COMMENT '稀释每股收益 (元)',
  `non_gaap_eps` DECIMAL(15,4) DEFAULT NULL COMMENT '扣非每股收益 (元)',
  `book_value_per_share` DECIMAL(15,4) DEFAULT NULL COMMENT '每股净资产 (元)',
  `capital_reserve_per_share` DECIMAL(15,4) DEFAULT NULL COMMENT '每股公积金 (元)',
  `undistributed_profit_per_share` DECIMAL(15,4) DEFAULT NULL COMMENT '每股未分配利润 (元)',
  `operating_cash_flow_per_share` DECIMAL(15,4) DEFAULT NULL COMMENT '每股经营现金流 (元)',

  -- ========== 盈利能力 ========== 
  `total_operating_revenue` DECIMAL(24,4) DEFAULT NULL COMMENT '营业总收入 (元)',
  `gross_profit` DECIMAL(20,4) DEFAULT NULL COMMENT '毛利润 (元)',
  `net_profit` DECIMAL(20,4) DEFAULT NULL COMMENT '归属净利润 (元)',
  `non_gaap_net_profit` DECIMAL(20,4) DEFAULT NULL COMMENT '扣非净利润 (元)',
  `roe_wa` DECIMAL(15,4) DEFAULT NULL COMMENT '净资产收益率 (加权)(%)',
  `roe_nwa` DECIMAL(15,4) DEFAULT NULL COMMENT '净资产收益率 (扣非加权)(%)',
  `roa_wa` DECIMAL(15,4) DEFAULT NULL COMMENT '净资产收益率 (加权)(%)',
  `gross_margin` DECIMAL(15,4) DEFAULT NULL COMMENT '毛利率 (%)',
  `net_margin` DECIMAL(15,4) DEFAULT NULL COMMENT '净利率 (%)',
  `actual_tax_rate` DECIMAL(15,4) DEFAULT NULL COMMENT '实际税率 (%)',

  -- ========== 成长能力 ========== 
  `yoy_total_operating_revenue` DECIMAL(15,4) DEFAULT NULL COMMENT '营业总收入同比增长 (%)',
  `yoy_net_profit` DECIMAL(15,4) DEFAULT NULL COMMENT '归属净利润同比增长 (%)',
  `yoy_non_gaap_net_profit` DECIMAL(15,4) DEFAULT NULL COMMENT '扣非净利润同比增长 (%)',
  `qoq_total_operating_revenue` DECIMAL(15,4) DEFAULT NULL COMMENT '营业总收入滚动环比增长 (%)',
  `qoq_net_profit` DECIMAL(15,4) DEFAULT NULL COMMENT '归属净利润滚动环比增长 (%)',
  `qoq_non_gaap_net_profit` DECIMAL(15,4) DEFAULT NULL COMMENT '扣非净利润滚动环比增长 (%)',

  -- ========== 收益质量 ========== 
  `advance_receipts_to_revenue` DECIMAL(15,4) DEFAULT NULL COMMENT '预收账款 / 营业收入',
  `net_sales_cash_to_revenue` DECIMAL(15,4) DEFAULT NULL COMMENT '销售净现金流 / 营业收入',
  `operating_cash_flow_to_revenue` DECIMAL(15,4) DEFAULT NULL COMMENT '经营净现金流 / 营业收入',

  -- ========== 财务风险 ========== 
  `current_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '流动比率',
  `quick_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '速动比率',
  `cash_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '现金流量比率',
  `asset_liability_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '资产负债率 (%)',
  `equity_coefficient` DECIMAL(15,4) DEFAULT NULL COMMENT '权益系数',
  `equity_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '产权比率',

  -- ========== 营运能力 ========== 
  `total_asset_turnover_days` DECIMAL(15,4) DEFAULT NULL COMMENT '总资产周转天数 (天)',
  `inventory_turnover_days` DECIMAL(15,4) DEFAULT NULL COMMENT '存货周转天数 (天)',
  `accounts_receivable_turnover_days` DECIMAL(15,4) DEFAULT NULL COMMENT '应收账款周转天数 (天)',
  `total_asset_turnover_times` DECIMAL(15,4) DEFAULT NULL COMMENT '总资产周转率 (次)',
  `inventory_turnover_times` DECIMAL(15,4) DEFAULT NULL COMMENT '存货周转率 (次)',
  `accounts_receivable_turnover_times` DECIMAL(15,4) DEFAULT NULL COMMENT '应收账款周转率 (次)',

  -- ========== 额外字段 ========== 
  `security_code` VARCHAR(20) DEFAULT NULL COMMENT '证券代码（纯数字）',
  `org_code` VARCHAR(30) DEFAULT NULL COMMENT '机构代码',
  `org_type` VARCHAR(255) DEFAULT NULL COMMENT '机构类型',
  `report_type` VARCHAR(255) DEFAULT NULL COMMENT '报告类型',
  `report_date_name` VARCHAR(255) DEFAULT NULL COMMENT '报告期名称',
  `security_type_code` VARCHAR(10) DEFAULT NULL COMMENT '证券类型代码',
  `notice_date` DATE DEFAULT NULL COMMENT '公告日期',
  `update_date` DATE DEFAULT NULL COMMENT '更新日期',
  `currency` VARCHAR(255) DEFAULT NULL COMMENT '货币单位',
  `report_year` VARCHAR(255) DEFAULT NULL COMMENT '报告年份',
  `epsjbtz` DECIMAL(15,4) DEFAULT NULL COMMENT '基本每股收益同比增长率',
  `bps_tz` DECIMAL(15,4) DEFAULT NULL COMMENT '每股净资产同比增长率',
  `mgzbgjtz` DECIMAL(15,4) DEFAULT NULL COMMENT '每股资本公积同比增长率',
  `mgwfplrtz` DECIMAL(15,4) DEFAULT NULL COMMENT '每股未分配利润同比增长率',
  `mgjyxjjetz` DECIMAL(15,4) DEFAULT NULL COMMENT '每股经营现金流同比增长率',
  `roejqtz` DECIMAL(15,4) DEFAULT NULL COMMENT '净资产收益率同比增长率',
  `zzcjlltz` DECIMAL(15,4) DEFAULT NULL COMMENT '总资产收益率同比增长率',
  `roictz` DECIMAL(15,4) DEFAULT NULL COMMENT 'ROIC同比增长率',
  `xsml_l_tb` DECIMAL(15,4) DEFAULT NULL COMMENT '毛利率同比变动',
  `yyzsrgdhbzc` DECIMAL(15,4) DEFAULT NULL COMMENT '营业收入/固定资产',
  `netprofitrphbzc` DECIMAL(15,4) DEFAULT NULL COMMENT '净利润/固定资产',
  `kfjlrgdhbzc` DECIMAL(15,4) DEFAULT NULL COMMENT '扣非净利润/固定资产',
  `prepaid_accounts_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '预付账款占比',
  `accounts_payable_tr` DECIMAL(15,4) DEFAULT NULL COMMENT '应付账款周转率',
  `fixed_asset_tr` DECIMAL(15,4) DEFAULT NULL COMMENT '固定资产周转率',
  `current_asset_tr` DECIMAL(15,4) DEFAULT NULL COMMENT '流动资产周转率',
  `prepaid_accounts_tdays` DECIMAL(15,4) DEFAULT NULL COMMENT '预付账款周转天数',
  `payable_tdays` DECIMAL(15,4) DEFAULT NULL COMMENT '应付账款周转天数',
  `operate_cycle` DECIMAL(15,4) DEFAULT NULL COMMENT '营运周期',
  `guard_speed_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '保守速动比率',
  `interest_coverage_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '利息保障倍数',
  `ca_ta` DECIMAL(15,4) DEFAULT NULL COMMENT '流动资产/总资产',
  `nca_ta` DECIMAL(15,4) DEFAULT NULL COMMENT '非流动资产/总资产',
  `liquidation_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '清算比率',
  `interest_debt_ratio` DECIMAL(15,4) DEFAULT NULL COMMENT '利息债务比',
  `fc_liabilities` DECIMAL(15,4) DEFAULT NULL COMMENT '金融负债占比',
  `liability` DECIMAL(20,4) DEFAULT NULL COMMENT '总负债',
  `fcff_forward` DECIMAL(20,4) DEFAULT NULL COMMENT '前瞻自由现金流',
  `fcff_back` DECIMAL(20,4) DEFAULT NULL COMMENT '回顾自由现金流',
  `ss_oi` DECIMAL(15,4) DEFAULT NULL COMMENT '销售费用/营业收入',
  `ss_ta` DECIMAL(15,4) DEFAULT NULL COMMENT '销售费用/总资产',
  `nco_op` DECIMAL(15,4) DEFAULT NULL COMMENT '净经营资产/营业收入',
  `nco_netprofit` DECIMAL(15,4) DEFAULT NULL COMMENT '净经营资产/净利润',
  `nco_fixed` DECIMAL(15,4) DEFAULT NULL COMMENT '净经营资产/固定资产',
  `roic` DECIMAL(15,4) DEFAULT NULL COMMENT '投资资本回报率',
  `djd_toi_yoy` DECIMAL(15,4) DEFAULT NULL COMMENT '营业总收入同比增速（单季度）',
  `djd_dpnp_yoy` DECIMAL(15,4) DEFAULT NULL COMMENT '归属净利润同比增速（单季度）',
  `djd_deductdpnp_yoy` DECIMAL(15,4) DEFAULT NULL COMMENT '扣非净利润同比增速（单季度）',
  `per_toi` DECIMAL(15,4) DEFAULT NULL COMMENT '市销率（TTM）',
  `per_oi` DECIMAL(15,4) DEFAULT NULL COMMENT '市销率（报告期）',
  `per_ebit` DECIMAL(15,4) DEFAULT NULL COMMENT '市盈率（EBIT）',
  `zcfzltz` DECIMAL(15,4) DEFAULT NULL COMMENT '资产负债率同比变动',

  -- 系统字段
  `created` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

  -- 主键
  PRIMARY KEY (`id`),

  -- 唯一索引（pmid）
  UNIQUE KEY `uk_pmid` (`pmid`),

  -- 普通索引（提升查询效率）
  INDEX `idx_stock_code` (`stock_code`),
  INDEX `idx_report_date` (`report_date`),
  INDEX `idx_stock_date` (`stock_code`, `report_date`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='上市企业-财务分析';