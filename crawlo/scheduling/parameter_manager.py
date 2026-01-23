"""
参数管理模块
负责定时任务参数的统一配置和管理
"""

from typing import Dict, Optional, Any
from crawlo.settings.setting_manager import SettingManager as Settings
from crawlo.logging import get_logger


class ParameterManager:
    """参数管理器"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.logger = get_logger("ParameterManager")
        
    async def get_job_parameters(self, job_name: str, original_args: Dict[str, Any]) -> Dict[str, Any]:
        """获取任务参数
        
        Args:
            job_name: 任务名称
            original_args: 原始参数
            
        Returns:
            完整的任务参数
        """
        # 1. 确定运行模式
        run_mode = self._get_run_mode(original_args)
        self.logger.debug(f"Run mode determined as: {run_mode} for job: {job_name}")
        
        # 2. 检查Redis可用性
        redis_available = await self._check_redis_availability()
        self.logger.debug(f"Redis availability result: {redis_available} for job: {job_name}")
        
        # 3. 获取队列配置
        queue_config = await self._get_queue_config(run_mode, redis_available, original_args)
        
        # 4. 构建完整参数
        parameters = self._build_parameters(queue_config, original_args)
        
        return parameters
    
    def _get_run_mode(self, original_args: Dict[str, Any]) -> str:
        """获取运行模式
        
        Args:
            original_args: 原始参数
            
        Returns:
            运行模式
        """
        return original_args.get('RUN_MODE', self.settings.get('RUN_MODE', 'standalone'))
    
    async def _check_redis_availability(self) -> bool:
        """检查Redis是否可用
        
        Returns:
            Redis是否可用
        """
        from crawlo.utils.redis_manager import get_redis_manager
        
        try:
            redis_manager = get_redis_manager()
            await redis_manager.ping()
            return True
        except Exception as e:
            self.logger.debug(f"Redis connection test failed: {e}")
            return False
    
    async def _get_queue_config(self, run_mode: str, redis_available: bool, original_args: Dict[str, Any]) -> Dict[str, Any]:
        """获取队列配置
        
        Args:
            run_mode: 运行模式
            redis_available: Redis是否可用
            original_args: 原始参数
            
        Returns:
            队列配置
        """
        if run_mode == 'distributed':
            if redis_available:
                return self._get_redis_config(original_args)
            else:
                raise RuntimeError("Distributed mode requires Redis, but Redis is unavailable")
        elif run_mode == 'auto':
            if redis_available:
                self.logger.info(f"Auto mode: Redis is available, using Redis config")
                return self._get_redis_config(original_args)
            else:
                self.logger.info(f"Auto mode: Redis is unavailable, using memory config")
                return self._get_memory_config(original_args)
        elif run_mode == 'standalone':
            return self._get_memory_config(original_args)
        else:
            return self._get_memory_config(original_args)
    
    def _get_redis_config(self, original_args: Dict[str, Any]) -> Dict[str, Any]:
        """获取Redis配置
        
        Args:
            original_args: 原始参数
            
        Returns:
            Redis配置
        """
        run_mode = original_args.get('RUN_MODE', 'distributed')
        return {
            'QUEUE_TYPE': 'redis',
            'FILTER_CLASS': original_args.get('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter'),
            'DEFAULT_DEDUP_PIPELINE': original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'),
            'RUN_MODE': run_mode
        }
    
    def _get_memory_config(self, original_args: Dict[str, Any]) -> Dict[str, Any]:
        """获取内存配置
        
        Args:
            original_args: 原始参数
            
        Returns:
            内存配置
        """
        run_mode = original_args.get('RUN_MODE', 'standalone')
        return {
            'QUEUE_TYPE': 'memory',
            'FILTER_CLASS': original_args.get('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter'),
            'DEFAULT_DEDUP_PIPELINE': original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'),
            'RUN_MODE': run_mode
        }
    
    def _build_parameters(self, queue_config: Dict[str, Any], original_args: Dict[str, Any]) -> Dict[str, Any]:
        """构建完整参数
        
        Args:
            queue_config: 队列配置
            original_args: 原始参数
            
        Returns:
            完整的任务参数
        """
        parameters = {}
        
        # 1. 添加队列配置
        parameters.update(queue_config)
        
        # 2. 从原始参数中复制其他配置项，但排除已处理的配置项
        excluded_keys = {
            'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_DB', 'REDIS_URL',
            'FILTER_CLASS', 'DEFAULT_DEDUP_PIPELINE', 'QUEUE_TYPE', 'RUN_MODE'
        }
        for key, value in original_args.items():
            if key not in excluded_keys:
                parameters[key] = value
        
        # 3. 添加调度器内部标识
        parameters['_INTERNAL_SCHEDULER_TASK'] = True
        
        # 4. 添加监控配置
        self._add_monitoring_config(parameters, queue_config)
        
        return parameters
    
    def _add_monitoring_config(self, parameters: Dict[str, Any], queue_config: Dict[str, Any]):
        """添加监控配置
        
        Args:
            parameters: 任务参数
            queue_config: 队列配置
        """
        # 获取运行模式和队列类型
        run_mode = queue_config.get('RUN_MODE', 'standalone')
        queue_type = queue_config.get('QUEUE_TYPE', 'memory')
        
        # 从项目配置中获取监控相关设置
        monitor_configs = [
            ('MEMORY_MONITOR_ENABLED', bool, False),
            ('MEMORY_MONITOR_INTERVAL', int, 30),
            ('MEMORY_WARNING_THRESHOLD', float, 80.0),
            ('MEMORY_CRITICAL_THRESHOLD', float, 90.0),
            ('MYSQL_MONITOR_ENABLED', bool, False),
            ('MYSQL_MONITOR_INTERVAL', int, 60),
            ('REDIS_MONITOR_ENABLED', bool, False),
            ('REDIS_MONITOR_INTERVAL', int, 60),
        ]
        
        for config_key, config_type, default_value in monitor_configs:
            if config_key not in parameters:
                if config_type == bool:
                    parameters[config_key] = self.settings.get_bool(config_key, default_value)
                elif config_type == int:
                    parameters[config_key] = self.settings.get_int(config_key, default_value)
                elif config_type == float:
                    parameters[config_key] = self.settings.get_float(config_key, default_value)
        
        # 根据运行模式和队列类型来决定是否启用Redis监控
        if run_mode == 'distributed' or (run_mode == 'auto' and queue_type == 'redis'):
            # 如果是distributed模式或auto模式下使用了Redis队列，则启用Redis监控
            # 但首先检查项目配置中是否设置了REDIS_MONITOR_ENABLED
            project_redis_monitor_enabled = self.settings.get_bool('REDIS_MONITOR_ENABLED', False)
            parameters['REDIS_MONITOR_ENABLED'] = project_redis_monitor_enabled
        else:
            # standalone模式或其他不需要Redis的情况，关闭Redis监控
            parameters['REDIS_MONITOR_ENABLED'] = False
        
        # 根据运行模式来决定是否启用内存监控
        if run_mode == 'distributed':
            # 在分布式模式下，可能需要内存监控来监控各个节点
            project_memory_monitor_enabled = self.settings.get_bool('MEMORY_MONITOR_ENABLED', False)
            parameters['MEMORY_MONITOR_ENABLED'] = project_memory_monitor_enabled
        else:
            # 在standalone和auto模式下，调度器已经有资源监控，避免重复
            parameters['MEMORY_MONITOR_ENABLED'] = False
