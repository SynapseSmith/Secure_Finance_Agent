#!/bin/bash
# Ollama 설정 스크립트

echo "🦙 Ollama 설정 시작..."

# Ollama 컨테이너 시작
docker-compose -f docker-compose.yml -f docker-compose.vllm.yml up -d ollama

echo "⏳ Ollama 준비 중..."
sleep 5

# 모델 다운로드
echo "📥 Llama 3 모델 다운로드 중..."
docker exec finance-agent-ollama ollama pull llama3:70b

# 또는 더 작은 모델
# docker exec finance-agent-ollama ollama pull llama3:8b
# docker exec finance-agent-ollama ollama pull mistral
# docker exec finance-agent-ollama ollama pull qwen2.5:72b

echo "✅ Ollama 설정 완료!"
echo "API 엔드포인트: http://localhost:11434"
echo ""
echo "사용 가능한 모델:"
docker exec finance-agent-ollama ollama list
