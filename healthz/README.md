# Health Check Container (healthz)

프로덕션급 컨테이너 헬스체크 시스템

## 📋 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [설정 가이드](#설정-가이드)
- [API 엔드포인트](#api-엔드포인트)
- [배포 가이드](#배포-가이드)

## 개요

**healthz**는 컨테이너 환경에서 애플리케이션의 상태를 모니터링하기 위한 표준화된 헬스체크 시스템입니다.

### 주요 특징

- ✅ **표준 준수**: Kubernetes, Docker 헬스체크 표준 준수
- 🔧 **모듈화 설계**: 각 체크 항목이 독립적으로 동작
- 📊 **상세 로깅**: 콘솔/파일 로그 분리, 일별 로테이션
- ⚙️ **유연한 설정**: YAML 기반 설정, 환경 변수 오버라이드
- 🚀 **프로덕션 준비**: Docker, Kubernetes 배포 설정 포함

## 주요 기능

### 1. 포트 체크 (Port Check)
- TCP 포트 리스닝 상태 확인
- 다중 포트 지원 (AND/OR 조건)
- 연결 타임아웃 설정

### 2. 프로세스 체크 (Process Check)
- 실행 중인 프로세스 확인
- 프로세스 이름/커맨드라인 기반 매칭
- 다중 프로세스 지원 (AND/OR 조건)

### 3. HTTP 엔드포인트 체크 (HTTP Check)
- 외부/내부 API 엔드포인트 상태 확인
- HTTP 상태 코드 검증
- 응답 본문 패턴 매칭

### 4. 리소스 체크 (Resource Check)
- CPU 사용률 모니터링
- 메모리 사용률 모니터링
- 디스크 사용률 모니터링

### 5. 로깅 시스템
- 콘솔/파일 로그 분리 설정
- 레벨별 필터링 (DEBUG, INFO, WARN, ERROR, CRITICAL)
- 일별 로그 파일 생성 및 크기 기반 로테이션
- JSON/텍스트 포맷 지원

## 프로젝트 구조

```
/opt/healthz/
├── app/
│   ├── __init__.py           # 패키지 초기화
│   ├── main.py               # 메인 애플리케이션 (Flask 서버)
│   ├── config.py             # 설정 로더
│   ├── logging_utils.py      # 로깅 유틸리티
│   └── checks/
│       ├── __init__.py
│       ├── base.py           # 베이스 체커 클래스
│       ├── port.py           # 포트 체커
│       ├── process.py        # 프로세스 체커
│       ├── http.py           # HTTP 체커
│       └── resource.py       # 리소스 체커
├── config.yaml               # 메인 설정 파일
├── requirements.txt          # Python 의존성
├── Dockerfile                # Docker 이미지 빌드
├── docker-compose.yml        # Docker Compose 설정
├── k8s-deployment.yaml       # Kubernetes 배포 설정
└── README.md                 # 본 문서
```

## 설치 및 실행

### 로컬 실행

```bash
# 1. 의존성 설치
cd /opt/healthz
pip install -r requirements.txt

# 2. 애플리케이션 실행
python -m app.main

# 3. 헬스체크 확인
curl http://localhost:8080/health
```

### Docker 실행

```bash
# 1. 이미지 빌드
docker build -t healthz:latest .

# 2. 컨테이너 실행
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/opt/healthz/config.yaml:ro \
  -v $(pwd)/logs:/opt/healthz/logs \
  --name healthz \
  healthz:latest

# 3. 로그 확인
docker logs -f healthz
```

### Docker Compose 실행

```bash
# 1. 서비스 시작
docker-compose up -d

# 2. 상태 확인
docker-compose ps

# 3. 로그 확인
docker-compose logs -f healthz
```

### Kubernetes 배포

```bash
# 1. ConfigMap 및 Deployment 배포
kubectl apply -f k8s-deployment.yaml

# 2. 파드 상태 확인
kubectl get pods -l app=healthz

# 3. 서비스 확인
kubectl get svc healthz-service

# 4. 로그 확인
kubectl logs -l app=healthz -f
```

## 설정 가이드

### config.yaml 구조

```yaml
# 서버 설정
server:
  host: 0.0.0.0      # 바인드 주소
  port: 8080         # 리스닝 포트
  debug: false       # 디버그 모드

# 로깅 설정
logging:
  console:
    enabled: true    # 콘솔 로그 활성화
    level: INFO      # 로그 레벨
  file:
    enabled: true    # 파일 로그 활성화
    level: WARN      # 파일 로그 레벨
    directory: /opt/healthz/logs
    filename_pattern: "healthz-{date}.log"
    max_size_mb: 10  # 최대 파일 크기
    rotation: daily  # 로테이션 주기

# 체크 설정
checks:
  ports:
    enabled: true
    targets: [8080, 80, 3000]
    condition: any   # any | all
    timeout: 5
  
  processes:
    enabled: true
    targets: ["python", "gunicorn", "celery"]
    condition: any   # any | all
    match_type: name # name | cmdline
  
  http:
    enabled: true
    targets:
      - url: "http://localhost:8080/api/health"
        method: GET
        timeout: 5
        expected_status: 200
  
  resources:
    enabled: true
    cpu:
      enabled: true
      threshold: 90
    memory:
      enabled: true
      threshold: 85
    disk:
      enabled: true
      threshold: 90
      path: /
```

### 환경 변수 오버라이드

설정 파일의 값을 환경 변수로 오버라이드할 수 있습니다:

```bash
# 서버 포트 변경
export SERVER_PORT=9090

# 로그 레벨 변경
export LOG_CONSOLE_LEVEL=DEBUG
export LOG_FILE_LEVEL=ERROR

# 체크 대상 변경
export CHECK_PORTS=8080,18080
export CHECK_PROCESS_NAMES=python,main
```

## API 엔드포인트

### 1. `/health` - 종합 헬스체크
```bash
curl http://localhost:8080/health
```

**응답 예시** (정상):
```json
{
  "status": "healthy",
  "timestamp": "2025-05-10T12:00:00Z",
  "checks": {
    "ports": {"status": "healthy", "details": "2/2 ports listening"},
    "processes": {"status": "healthy", "details": "2/3 processes running"},
    "resources": {"status": "healthy", "details": "All resources within limits"}
  }
}
```

### 2. `/healthz` - Kubernetes 스타일 헬스체크
```bash
curl http://localhost:8080/healthz
```

### 3. `/livez` - Liveness Probe
```bash
curl http://localhost:8080/livez
```

### 4. `/readyz` - Readiness Probe
```bash
curl http://localhost:8080/readyz
```

## 배포 가이드

### Docker 프로덕션 배포

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  healthz:
    image: healthz:latest
    ports:
      - "8080:8080"
    environment:
      - SERVER_PORT=8080
      - LOG_CONSOLE_LEVEL=INFO
      - LOG_FILE_LEVEL=WARN
    volumes:
      - ./config.yaml:/opt/healthz/config.yaml:ro
      - healthz-logs:/opt/healthz/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

volumes:
  healthz-logs:
    driver: local
```

### Kubernetes 프로덕션 배포

```bash
# 1. ConfigMap 생성
kubectl create configmap healthz-config \
  --from-file=config.yaml=./config.yaml

# 2. Deployment 배포
kubectl apply -f k8s-deployment.yaml

# 3. HPA 설정 (선택사항)
kubectl autoscale deployment healthz-deployment \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

## 모니터링 및 알림

### Prometheus 메트릭 (향후 추가 예정)

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'healthz'
    static_configs:
      - targets: ['healthz-service:8080']
```

### Grafana 대시보드 (향후 추가 예정)

헬스체크 메트릭을 시각화하는 Grafana 대시보드를 제공할 예정입니다.

## 트러블슈팅

### 로그 확인

```bash
# Docker
docker logs healthz

# Kubernetes
kubectl logs -l app=healthz -f

# 파일 로그
tail -f /opt/healthz/logs/healthz-$(date +%Y%m%d).log
```

### 일반적인 문제

1. **포트 체크 실패**
   - 대상 애플리케이션이 실행 중인지 확인
   - 포트 번호가 올바른지 확인
   - 방화벽 규칙 확인

2. **프로세스 체크 실패**
   - 프로세스 이름이 정확한지 확인
   - `ps aux | grep <process_name>` 로 확인

3. **리소스 체크 실패**
   - 임계값 조정 필요 여부 확인
   - 시스템 리소스 증설 검토

## 라이선스

MIT License

## 작성자

HaeDong - Senior Infrastructure & Data Platform Engineer

## 참고 자료

- [Kubernetes Liveness/Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Docker HEALTHCHECK](https://docs.docker.com/engine/reference/builder/#healthcheck)
- [Microservices Health Check API Pattern](https://microservices.io/patterns/observability/health-check-api.html)
