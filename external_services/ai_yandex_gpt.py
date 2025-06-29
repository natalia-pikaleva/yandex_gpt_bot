

"""
3. Альтернативный способ — llama-cpp-python
Можно использовать Python-обёртку [llama-cpp-python]:

python
from llama_cpp import Llama

llm = Llama(model_path="models/YandexGPT-5-Lite-8B-instruct-GGUF/YandexGPT-5-Lite-8B-instruct-Q4_K_M.gguf", n_ctx=32768)
prompt = "Текст: ...ваш текст...\n---\nВопрос: ...ваш вопрос..."
output = llm(prompt, max_tokens=512)
print(output["choices"][0]["text"])
"""