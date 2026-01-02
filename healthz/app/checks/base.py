"""
베이스 체커 모듈

모든 체커의 부모 클래스를 정의합니다.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """
    체크 결과 데이터 클래스
    
    Attributes:
        name: 체크 이름
        status: 상태 ('UP' 또는 'DOWN')
        message: 상태 메시지
        details: 상세 정보
        timestamp: 체크 시간
        duration_ms: 체크 소요 시간 (밀리초)
    """
    name: str
    status: str  # 'UP' or 'DOWN'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    duration_ms: float = 0.0
    
    def is_healthy(self) -> bool:
        """정상 상태인지 확인"""
        return self.status == 'UP'
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'name': self.name,
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp,
            'duration_ms': self.duration_ms
        }


class BaseChecker(ABC):
    """
    헬스체커 베이스 클래스
    
    모든 체커는 이 클래스를 상속받아야 합니다.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        베이스 체커 초기화
        
        Args:
            name: 체커 이름
            config: 설정 딕셔너리
        """
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def check(self) -> CheckResult:
        """
        헬스체크를 수행합니다.
        
        Returns:
            CheckResult: 체크 결과
        """
        pass
    
    def is_enabled(self) -> bool:
        """체커가 활성화되어 있는지 확인"""
        return self.enabled
    
    def _create_result(
        self,
        status: str,
        message: str,
        details: Dict[str, Any] = None,
        duration_ms: float = 0.0
    ) -> CheckResult:
        """
        CheckResult 객체를 생성합니다.
        
        Args:
            status: 상태 ('UP' 또는 'DOWN')
            message: 메시지
            details: 상세 정보
            duration_ms: 소요 시간
        
        Returns:
            CheckResult: 체크 결과
        """
        return CheckResult(
            name=self.name,
            status=status,
            message=message,
            details=details or {},
            duration_ms=duration_ms
        )
