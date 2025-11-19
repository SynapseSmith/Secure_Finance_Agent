#!/bin/bash
# vLLM 설정 스크립트

echo "🚀 vLLM 설정 시작..."

# GPU 확인
if ! command -v nvidia-smi &> /dev/null; then
    echo "⚠️  NVIDIA GPU가 감지되지 않았습니다."
    echo "CPU 모드로는 Ollama 사용을 권장합니다."
    exit 1
fi

echo "✅ GPU 감지됨"
nvidia-smi

# Docker Compose 파일 병합
echo "📦 vLLM 서비스 시작..."
docker-compose -f docker-compose.yml -f docker-compose.vllm.yml up -d vllm

echo "⏳ 모델 다운로드 중... (시간이 걸릴 수 있습니다)"
docker-compose logs -f vllm

echo "✅ vLLM 설정 완료!"
echo "API 엔드포인트: http://localhost:8001/v1"
