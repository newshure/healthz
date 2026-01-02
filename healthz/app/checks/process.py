"""
프로세스 체크 모듈
지정된 프로세스가 실행 중인지 확인합니다.
"""

import time
import psutil
from typing import Dict, Any, List, Tuple
from .base import BaseChecker, CheckResult


class ProcessChecker(BaseChecker):
    """프로세스 실행 상태를 체크하는 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('processes', config)
        self.targets: List[str] = config.get('targets', ['python'])
        self.condition = config.get('condition', 'any')
        self.match_type = config.get('match_type', 'partial')
        self.logger.debug(f"프로세스 체커 초기화: {self.targets}")
    
    def check(self) -> CheckResult:
        start_time = time.time()
        self.logger.debug(f"프로세스 체크 시작: {self.targets}")
        
        results = {}
        success_count = 0
        
        for process_name in self.targets:
            is_running, count = self._check_process(process_name)
            results[process_name] = {'status': 'UP' if is_running else 'DOWN', 'running': is_running, 'count': count}
            if is_running:
                success_count += 1
        
        if self.condition == 'all':
            overall_status = 'UP' if success_count == len(self.targets) else 'DOWN'
            message = f"All {len(self.targets)} processes running" if overall_status == 'UP' else f"Only {success_count}/{len(self.targets)} processes running"
        else:
            overall_status = 'UP' if success_count > 0 else 'DOWN'
            message = f"At least one process running ({success_count}/{len(self.targets)})" if overall_status == 'UP' else "No processes running"
        
        duration_ms = (time.time() - start_time) * 1000
        
        if overall_status == 'UP':
            self.logger.debug(f"✅ 프로세스 체크 성공: {message}")
        else:
            self.logger.warning(f"⚠️  프로세스 체크 실패: {message}")
        
        return self._create_result(status=overall_status, message=message, details={'condition': self.condition, 'match_type': self.match_type, 'success_count': success_count, 'total_count': len(self.targets), 'processes': results}, duration_ms=duration_ms)
    
    def _check_process(self, process_name: str) -> Tuple[bool, int]:
        try:
            count = 0
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    cmdline = ' '.join(proc_info.get('cmdline', []))
                    if self.match_type == 'exact':
                        if proc_name == process_name:
                            count += 1
                    else:
                        if process_name in proc_name or process_name in cmdline:
                            count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            is_running = count > 0
            if is_running:
                self.logger.debug(f"  ✓ 프로세스 '{process_name}' 실행 중 ({count}개)")
            else:
                self.logger.debug(f"  ✗ 프로세스 '{process_name}' 실행 안 함")
            return is_running, count
        except Exception as e:
            self.logger.error(f"  ✗ 프로세스 체크 실패: {e}")
            return False, 0
