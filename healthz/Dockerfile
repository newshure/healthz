# ============================================================
# Dockerfile for Health Check Container (healthz)
# 헬스체크 컨테이너용 Dockerfile
# ============================================================

# Base Image - Python 3.11 Slim (작은 용량, 보안 패치 적용)
FROM python:3.11-slim

# Metadata - 컨테이너 메타데이터
LABEL maintainer="HaeDong <your-email@example.com>"
LABEL description="Production-grade health check container for monitoring applications"
LABEL version="1.0.0"

# Environment Variables - 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Working Directory - 작업 디렉토리 설정
WORKDIR /opt/healthz

# Install System Dependencies - 시스템 패키지 설치
# (필요한 경우: curl, net-tools, procps 등)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        net-tools \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Copy Requirements - 의존성 파일 복사
COPY requirements.txt .

# Install Python Dependencies - Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# Copy Application Code - 애플리케이션 코드 복사
COPY app/ ./app/
COPY config.yaml .

# Create Log Directory - 로그 디렉토리 생성
RUN mkdir -p /opt/healthz/logs && \
    chmod 755 /opt/healthz/logs

# Non-root User - 보안을 위한 비루트 사용자 생성
RUN useradd -m -u 1000 healthz && \
    chown -R healthz:healthz /opt/healthz

USER healthz

# Health Check - Docker 자체 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose Port - 헬스체크 서버 포트 노출
EXPOSE 8080

# Start Application - 애플리케이션 실행
# Development: Flask 내장 서버
CMD ["python", "-m", "app.main"]

# Production: Gunicorn 서버 (주석 해제하여 사용)
# CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "30", "app.main:app"]
