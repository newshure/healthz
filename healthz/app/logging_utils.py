"""
로깅 유틸리티 모듈

콘솔 및 파일 로깅을 설정합니다.
일별 로테이션 및 크기 기반 로테이션을 지원합니다.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class DailyRotatingFileHandler(TimedRotatingFileHandler):
    """
    일별 로테이션 파일 핸들러 (크기 제한 포함)
    
    매일 자정에 새 파일을 생성하고, 파일 크기가 제한을 초과하면
    즉시 로테이션을 수행합니다.
    """
    
    def __init__(self, filename_pattern: str, log_dir: str, 
                 max_bytes: int = 0, backup_count: int = 5):
        """
        DailyRotatingFileHandler 초기화
        
        Args:
            filename_pattern: 파일 이름 패턴 (예: healthz-{date}.log)
            log_dir: 로그 디렉토리
            max_bytes: 최대 파일 크기 (바이트)
            backup_count: 백업 파일 개수
        """
        self.log_dir = Path(log_dir)
        self.filename_pattern = filename_pattern
        self.max_bytes = max_bytes
        
        # 로그 디렉토리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 현재 날짜의 로그 파일명 생성
        current_filename = self._get_current_filename()
        
        # TimedRotatingFileHandler 초기화
        super().__init__(
            filename=str(self.log_dir / current_filename),
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # 파일명 포맷 지정 (날짜 suffix)
        self.suffix = "%Y-%m-%d"
    
    def _get_current_filename(self) -> str:
        """
        현재 날짜의 파일 이름을 생성합니다.
        
        Returns:
            str: 파일 이름
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.filename_pattern.replace('{date}', today)
    
    def emit(self, record):
        """
        로그 레코드를 출력하고 필요시 크기 기반 로테이션을 수행합니다.
        
        Args:
            record: 로그 레코드
        """
        # 크기 체크 및 로테이션
        if self.max_bytes > 0:
            try:
                if self.stream and os.path.exists(self.baseFilename):
                    file_size = os.path.getsize(self.baseFilename)
                    if file_size >= self.max_bytes:
                        self.doRollover()
            except Exception:
                pass
        
        # 부모 클래스의 emit 호출
        super().emit(record)


def setup_logging(config: Dict[str, Any]) -> None:
    """
    로깅 시스템을 설정합니다.
    
    Args:
        config: 로깅 설정 딕셔너리
    
    Example:
        >>> logging_config = {
        ...     'console': {
        ...         'enabled': True,
        ...         'level': 'INFO',
        ...         'format': 'text'
        ...     },
        ...     'file': {
        ...         'enabled': True,
        ...         'level': 'WARN',
        ...         'dir': '/var/log/healthz',
        ...         'filename_pattern': 'healthz-{date}.log',
        ...         'rotation': {
        ...             'max_size_mb': 10,
        ...             'backup_count': 5,
        ...             'daily': True
        ...         }
        ...     }
        ... }
        >>> setup_logging(logging_config)
    """
    # 루트 로거 가져오기
    root_logger = logging.getLogger()
    
    # 기존 핸들러 제거
    root_logger.handlers.clear()
    
    # 로그 레벨 매핑
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARN': logging.WARNING,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    
    # 루트 로거 레벨을 DEBUG로 설정 (핸들러에서 필터링)
    root_logger.setLevel(logging.DEBUG)
    
    handlers = []
    
    # -------------------------------------------------------------------------
    # 콘솔 핸들러 설정
    # -------------------------------------------------------------------------
    console_config = config.get('console', {})
    if console_config.get('enabled', True):
        console_level = console_config.get('level', 'INFO').upper()
        console_format = console_config.get('format', 'text')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_levels.get(console_level, logging.INFO))
        
        # 포맷 설정
        if console_format == 'json':
            # JSON 포맷
            formatter = logging.Formatter(
                '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                '"name":"%(name)s","message":"%(message)s"}'
            )
        else:
            # 텍스트 포맷
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
        
        print(f"✅ 콘솔 로그 활성화: 레벨={console_level}, 포맷={console_format}")
    
    # -------------------------------------------------------------------------
    # 파일 핸들러 설정
    # -------------------------------------------------------------------------
    file_config = config.get('file', {})
    if file_config.get('enabled', True):
        file_level = file_config.get('level', 'WARN').upper()
        log_dir = file_config.get('dir', '/opt/healthz/logs')
        filename_pattern = file_config.get('filename_pattern', 'healthz-{date}.log')
        rotation_config = file_config.get('rotation', {})
        
        max_size_mb = rotation_config.get('max_size_mb', 10)
        backup_count = rotation_config.get('backup_count', 5)
        daily = rotation_config.get('daily', True)
        
        # 로그 디렉토리 생성
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        if daily:
            # 일별 로테이션 + 크기 제한
            file_handler = DailyRotatingFileHandler(
                filename_pattern=filename_pattern,
                log_dir=log_dir,
                max_bytes=max_size_mb * 1024 * 1024,  # MB를 바이트로 변환
                backup_count=backup_count
            )
        else:
            # 크기 기반 로테이션만
            today = datetime.now().strftime("%Y-%m-%d")
            filename = filename_pattern.replace('{date}', today)
            filepath = Path(log_dir) / filename
            
            file_handler = RotatingFileHandler(
                filename=str(filepath),
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
        
        file_handler.setLevel(log_levels.get(file_level, logging.WARNING))
        
        # 파일 로그는 항상 상세한 텍스트 포맷 사용
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
        
        print(f"✅ 파일 로그 활성화: 레벨={file_level}, 디렉토리={log_dir}")
        print(f"   로테이션: 최대 크기={max_size_mb}MB, 백업={backup_count}개, 일별={daily}")
    
    # 핸들러 추가
    for handler in handlers:
        root_logger.addHandler(handler)
    
    if not handlers:
        print("⚠️  경고: 활성화된 로그 핸들러가 없습니다.")
    
    print()
