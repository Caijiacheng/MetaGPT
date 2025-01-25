
from openai import OpenAI

def get_openai_version():
    import openai
    return openai.__version__

# 使用函数
version = get_openai_version()
print(f"OpenAI 库的版本是：{version}")

client = OpenAI(api_key="sk-809abecd562240b4a8a9a9b79ec8a613", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant，返回中文"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)