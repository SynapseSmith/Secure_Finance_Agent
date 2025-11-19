# LLM 배포 가이드

프로젝트는 다양한 LLM 배포 방식을 지원합니다.

## 1. 외부 API 사용 (권장)

### Claude (Anthropic)
```bash
# .env 설정
LLM_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-xxx
```

### GPT-4 (OpenAI)
```bash
LLM_PROVIDER=openai
MODEL_NAME=gpt-4-turbo
OPENAI_API_KEY=sk-xxx
```

**장점:**
- 즉시 사용 가능
- 최신 모델
- 인프라 관리 불필요

**단점:**
- API 비용
- 외부 의존성
- 데이터 전송

---

## 2. vLLM 자체 호스팅 (GPU 필요)

### 요구사항
- NVIDIA GPU (A100, H100 권장)
- 최소 40GB VRAM (Llama-3-70B 기준)
- Docker + nvidia-docker

### 설정
```bash
# 1. GPU 확인
nvidia-smi

# 2. vLLM 시작
./scripts/setup-vllm.sh

# 3. .env 설정
LLM_PROVIDER=vllm
VLLM_API_BASE=http://localhost:8001/v1
VLLM_MODEL_NAME=meta-llama/Llama-3-70b-chat-hf
```

### 지원 모델
- Llama 3 (8B, 70B, 405B)
- Mistral (7B, 8x7B, 8x22B)
- Qwen 2.5 (7B, 72B)
- Yi (6B, 34B)

**장점:**
- 데이터 프라이버시
- API 비용 없음
- 낮은 레이턴시

**단점:**
- GPU 비용
- 인프라 관리
- 모델 업데이트 수동

---

## 3. Ollama (CPU/소형 GPU)

### 설정
```bash
# 1. Ollama 시작
./scripts/setup-ollama.sh

# 2. .env 설정
LLM_PROVIDER=ollama
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL_NAME=llama3:70b
```

### 추천 모델
```bash
# 작은 모델 (개발/테스트)
ollama pull llama3:8b      # 4.7GB
ollama pull mistral        # 4.1GB

# 중형 모델
ollama pull llama3:70b     # 39GB
ollama pull qwen2.5:72b    # 41GB
```

**장점:**
- 로컬 실행
- 쉬운 설정
- 무료

**단점:**
- CPU는 느림
- 성능 제한

---

## 4. LiteLLM (멀티 프로바이더)

여러 프로바이더를 통합 관리

```bash
LLM_PROVIDER=litellm
```

### 폴백 설정
```python
# 1차: Claude
# 2차: GPT-4
# 3차: vLLM
```

---

## 비교표

| 방식 | 비용 | 성능 | 프라이버시 | 설정 난이도 |
|------|------|------|-----------|-----------|
| Claude API | 💰💰💰 | ⭐⭐⭐⭐⭐ | ⚠️ | ⭐ |
| GPT-4 API | 💰💰💰 | ⭐⭐⭐⭐⭐ | ⚠️ | ⭐ |
| vLLM | 💰💰💰💰 | ⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐ |
| Ollama | 💰 | ⭐⭐⭐ | ✅ | ⭐⭐ |

---

## 금융권 추천

### 개발 환경
- **Ollama** (llama3:8b)
- 빠른 테스트, 비용 절감

### 스테이징
- **Claude API** 또는 **GPT-4**
- 실제 성능 확인

### 프로덕션
- **온프레미스**: vLLM (Llama-3-70B 이상)
- **클라우드**: Claude 3.5 Sonnet
- **하이브리드**: LiteLLM (폴백)

---

## 보안 고려사항

### 자체 호스팅 (vLLM/Ollama)
✅ 데이터가 외부로 나가지 않음
✅ 완전한 통제
✅ 규제 준수 용이

### API 사용
⚠️ 데이터 전송 (암호화 필수)
⚠️ 서비스 약관 검토
⚠️ 금융 데이터 처리 가능 여부 확인

---

## 성능 벤치마크

```bash
# 벤치마크 실행
python scripts/benchmark_llm.py
```

예상 결과:
- Claude 3.5: ~500ms
- GPT-4 Turbo: ~600ms
- vLLM (A100): ~200ms
- Ollama (CPU): ~5000ms
