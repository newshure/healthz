"""
포트 체크 모듈
지정된 포트가 리스닝 중인지 확인합니다.
"""

import time
import socket
from typing import Dict, Any, List

from .base import BaseChecker, CheckResult


class PortChecker(BaseChecker):
    """포트 리스닝 상태를 체크하는 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('ports', config)
        self.targets: List[int] = config.get('targets', [8080])
        self.condition = config.get('condition', 'all')
        self.timeout = config.get('timeout', 2)
        self.logger.debug(f"포트 체커 초기화: {self.targets}")
    
    def check(self) -> CheckResult:
        start_time = time.time()
        self.logger.debug(f"포트 체크 시작: {self.targets}")
        
        results = {}
        success_count = 0
        
        for port in self.targets:
            is_listening = self._check_port(port)
            results[f"port_{port}"] = {
                'status': 'UP' if is_listening else 'DOWN',
                'port': port,
                'listening': is_listening
            }
            if is_listening:
                success_count += 1
        
        if self.condition == 'all':
            overall_status = 'UP' if success_count == len(self.targets) else 'DOWN'
            message = f"All {len(self.targets)} ports listening" if overall_status == 'UP' else f"Only {success_count}/{len(self.targets)} ports listening"
        else:
            overall_status = 'UP' if success_count > 0 else 'DOWN'
            message = f"At least one port listening ({success_count}/{len(self.targets)})" if overall_status == 'UP' else "No ports listening"
        
        duration_ms = (time.time() - start_time) * 1000
        
        if overall_status == 'UP':
            self.logger.debug(f"✅ 포트 체크 성공: {message}")
        else:
            self.logger.warning(f"⚠️  포트 체크 실패: {message}")
        
        return self._create_result(
            status=overall_status,
            message=message,
            details={'condition': self.condition, 'success_count': success_count, 'total_count': len(self.targets), 'ports': results},
            duration_ms=duration_ms
        )
    
    def _check_port(self, port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            is_listening = (result == 0)
            if is_listening:
                self.logger.debug(f"  ✓ 포트 {port} 리스닝 중")
            else:
                self.logger.debug(f"  ✗ 포트 {port} 닫혀 있음")
            return is_listening
        except Exception as e:
            self.logger.error(f"  ✗ 포트 {port} 체크 실패: {e}")
            return False
