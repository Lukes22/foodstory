我要做一个网页，后端希望使用python进行开发，实现一个web项目，每天用户进入以后会看到一段AI生成小故事，类似rpg打怪每日副本。用户拥有生命，理智，力量。输入一餐吃了什么，AI根据用户的回答，生成后面的剧情。比如可以给人物属性上buff和debuff,或者获得相应的装备。输入完一日三餐以后，用户看到故事的结局。然后用户可以看到好友今日生成的故事。

使用魔搭的API-Inference，有几个需要适配的有几个地方： • base url: 指向魔搭API-Inference服务 https://api-inference.modelscope.cn/v1/。 • api_key: 使用魔搭的访问令牌(Access Token) • 模型名字(model):使用魔搭上开源模型的Qwen/Qwen3-32B

Qwen/Qwen3-32B的一个使用范例如下：

from openai import OpenAI

client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key='ms-7537e3f2-17c4-48df-8d70-55431394642a', # ModelScope Token
)

# set extra_body for thinking control
extra_body = {
    # enable thinking, set to False to disable test
    "enable_thinking": True,
    # use thinking_budget to contorl num of tokens used for thinking
    # "thinking_budget": 4096
}

response = client.chat.completions.create(
    model='Qwen/Qwen3-32B', # ModelScope Model-Id, required
    messages=[
        {
          'role': 'user',
          'content': '9.9和9.11谁大'
        }
    ],
    stream=True,
    extra_body=extra_body
)
done_thinking = False
for chunk in response:
    if chunk.choices:
        thinking_chunk = chunk.choices[0].delta.reasoning_content
        answer_chunk = chunk.choices[0].delta.content
        if thinking_chunk != '':
            print(thinking_chunk, end='', flush=True)
        elif answer_chunk != '':
            if not done_thinking:
                print('\n\n === Final Answer ===\n')
                done_thinking = True
            print(answer_chunk, end='', flush=True)