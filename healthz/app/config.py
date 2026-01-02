"""
설정 로더 모듈

YAML 설정 파일을 읽고 파싱합니다.
환경 변수를 통한 오버라이드를 지원합니다.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Config:
    """
    설정 클래스
    
    YAML 파일에서 설정을 로드하고 환경 변수로 오버라이드합니다.
    
    Attributes:
        config (Dict[str, Any]): 설정 딕셔너리
        config_path (str): 설정 파일 경로
    """
    
    def __init__(self, config_path: str = '/opt/healthz/config.yaml'):
        """
        Config 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> None:
        """YAML 설정 파일을 로드합니다."""
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            logger.warning(f"설정 파일을 찾을 수 없음: {config_path}")
            logger.warning("기본 설정을 사용합니다.")
            self.config = self._get_default_config()
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                logger.info(f"설정 파일 로드 완료: {config_path}")
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            logger.warning("기본 설정을 사용합니다.")
            self.config = self._get_default_config()
    
    def _apply_env_overrides(self) -> None:
        """환경 변수로 설정을 오버라이드합니다."""
        # 주요 설정을 환경 변수로 오버라이드
        env_mappings = {
            'APP_NAME': ['application', 'name'],
            'APP_VERSION': ['application', 'version'],
            'ENVIRONMENT': ['application', 'environment'],
            'SERVER_HOST': ['server', 'host'],
            'SERVER_PORT': ['server', 'port'],
            'LOG_LEVEL': ['logging', 'console', 'level'],
            'LOG_FORMAT': ['logging', 'console', 'format'],
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                # SERVER_PORT는 정수로 변환
                if env_var == 'SERVER_PORT':
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        logger.warning(f"잘못된 SERVER_PORT 값: {env_value}, 무시됨")
                        continue
                
                self._set_nested(self.config, config_path, env_value)
                logger.debug(f"환경 변수 적용: {env_var}={env_value}")
    
    @staticmethod
    def _set_nested(d: Dict, keys: list, value: Any) -> None:
        """
        중첩된 딕셔너리에 값을 설정합니다.
        
        Args:
            d: 대상 딕셔너리
            keys: 키 경로 리스트
            value: 설정할 값
        """
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """
        기본 설정을 반환합니다.
        
        Returns:
            Dict[str, Any]: 기본 설정 딕셔너리
        """
        return {
            'application': {
                'name': 'healthcheck-app',
                'version': '1.0.0',
                'environment': 'production'
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8080,
                'workers': 4,
                'timeout': 30
            },
            'endpoints': {
                'health': '/health',
                'healthz': '/healthz',
                'livez': '/livez',
                'readyz': '/readyz'
            },
            'logging': {
                'console': {
                    'enabled': True,
                    'level': 'INFO',
                    'format': 'text'
                },
                'file': {
                    'enabled': True,
                    'level': 'WARN',
                    'dir': '/opt/healthz/logs',
                    'filename_pattern': 'healthz-{date}.log',
                    'rotation': {
                        'max_size_mb': 10,
                        'backup_count': 5,
                        'daily': True
                    }
                },
                'log_success_checks': False,
                'log_requests': False
            },
            'checks': {
                'ports': {
                    'enabled': True,
                    'targets': [8080],
                    'condition': 'all',
                    'timeout': 2
                },
                'processes': {
                    'enabled': True,
                    'targets': ['python'],
                    'condition': 'any',
                    'match_type': 'partial'
                },
                'http': {
                    'enabled': False,
                    'endpoints': []
                },
                'resources': {
                    'cpu': {'enabled': False, 'threshold_percent': 90},
                    'memory': {'enabled': True, 'threshold_percent': 90},
                    'disk': {'enabled': True, 'threshold_percent': 85, 'paths': ['/']}
                }
            },
            'timing': {
                'initial_delay_seconds': 15,
                'period_seconds': 10,
                'timeout_seconds': 5,
                'failure_threshold': 3,
                'success_threshold': 1
            },
            'probes': {
                'liveness': {'checks': ['ports', 'processes']},
                'readiness': {'checks': ['ports', 'processes', 'http', 'resources']}
            }
        }
    
    def get(self, *keys, default=None) -> Any:
        """
        중첩된 설정 값을 가져옵니다.
        
        Args:
            *keys: 설정 키 경로
            default: 기본값
        
        Returns:
            Any: 설정 값 또는 기본값
        
        Example:
            >>> config.get('server', 'port')
            8080
            >>> config.get('checks', 'ports', 'enabled')
            True
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value


# 전역 설정 인스턴스
_config: Optional[Config] = None


def load_config(config_path: str = '/opt/healthz/config.yaml') -> Config:
    """
    설정을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로
    
    Returns:
        Config: Config 인스턴스
    """
    global _config
    _config = Config(config_path)
    return _config


def get_config() -> Config:
    """
    현재 설정 인스턴스를 반환합니다.
    
    Returns:
        Config: Config 인스턴스
    
    Raises:
        RuntimeError: 설정이 로드되지 않은 경우
    """
    if _config is None:
        raise RuntimeError("설정이 로드되지 않았습니다. load_config()를 먼저 호출하세요.")
    return _config
