import json
import re

from openai import OpenAI
from flask import current_app


def get_ai_client():
    return OpenAI(
        base_url=current_app.config['AI_BASE_URL'],
        api_key=current_app.config['AI_API_KEY'],
    )


SYSTEM_PROMPT = """你是一个RPG游戏系统"美食副本引擎"。你把玩家每餐吃的食物转化为RPG装备、药水和状态效果。

重要限制:
- 只根据玩家当前输入的食物生成装备和效果，绝对不要自己编造额外的食物、饮料或道具
- 开场白只输出副本信息，不提及任何具体食物，不生成装备或属性变化
- 每餐只处理玩家输入的食物，不要凭空添加其他食物内容
- 装备名称必须直接与玩家输入的食物相关，体现食物特征（如肉包子→盾牌，豆浆→药水）
- 检定时必须严格对比玩家当前属性值，属性值>=检定值才成功，否则失败，不要随意判定

核心风格:
- 幽默、略带自嘲和毒舌，像吐槽型游戏系统提示
- 装备和药水要有具体数值感，效果描述要结合食物的真实营养特性
- 食物越健康，装备品质越高；垃圾食品给负面装备或debuff
- 语言简洁，像游戏提示框，不要写长篇叙事

===== 开场白格式 =====
当用户请求开场白时，严格按以下格式输出（不输出JSON）:
【副本名称】（一个有趣的副本标题，如"食堂生存战""外卖迷宫""早八噩梦"等）
【副本背景】（一句话描述今天的日常场景，用RPG语言，30-50字）
【副本等级】（根据日期/星期随机：普通/困难/噩梦/地狱）
【当前身份】（一个幽默的RPG化身份标签，如"负重前行的早八员工""被ddl追杀的勇者"）

===== 用餐格式 =====
当用户输入食物后，严格按以下格式输出:

恭喜获得装备【装备名】！（属性数值描述）
附魔属性："附魔名" —— 附魔效果描述

获得药水【药水名】！（药水效果描述）

获得状态【状态名】！状态效果描述（1-2句话）

【生命+X】【敏捷+X】【力量+X】

（可选）【检定：属性名>数值，成功/失败！】检定结果的简短描述
注意检定：必须用玩家当前的实际属性值来判定，属性值>=阈值才算成功

然后在末尾输出JSON数据块，用 ```json 和 ``` 包裹:
```json
{
  "health_change": 数字,
  "sanity_change": 数字,
  "strength_change": 数字,
  "equipment": "装备名（不含【】）",
  "potion": "药水名（不含【】）"
}
```

===== 结局格式 =====
当晚餐结束后，在正常用餐内容之后，用 "=== 冒险结局 ===" 分隔，然后输出:
（一段50-80字的最终结局描述。如果今天整体饮食健康均衡，给出正向结局；如果整体不健康或营养不均，给出负向结局。结局必须明确是正向或负向。）
恭喜获得结局【结局名称】！

属性规则:
- 每项属性变化范围: -30 ~ +30
- 生命/敏捷/力量的值范围是0到200
- equipment和potion字段必须有值，不能为null
- 用中文回答"""

MEAL_LABELS = {
    'breakfast': '早餐',
    'lunch': '午餐',
    'dinner': '晚餐',
}


def build_opening_messages(date_str):
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {
            'role': 'user',
            'content': (
                f'今天是{date_str}，请生成今日副本开场白。'
                '严格按照开场白格式输出：【副本背景】【副本等级】【当前身份】三行，不要输出其他内容。'
                '不需要输出JSON数据块。'
            ),
        },
    ]


def build_meal_messages(story, food_input, meal_type):
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
    ]

    # Add opening context
    messages.append({
        'role': 'user',
        'content': f'今天是{story.date.strftime("%Y年%m月%d日")}，请为今天的冒险生成一段开场白。',
    })
    messages.append({
        'role': 'assistant',
        'content': story.opening_text,
    })

    # Add previous meals as conversation history
    for meal in story.meals.all():
        label = MEAL_LABELS.get(meal.meal_type, meal.meal_type)
        messages.append({
            'role': 'user',
            'content': f'我{label}吃了: {meal.food_input}',
        })
        # Reconstruct assistant response with JSON block
        json_block = json.dumps({
            'health_change': meal.health_change,
            'sanity_change': meal.sanity_change,
            'strength_change': meal.strength_change,
            'equipment': meal.equipment_gained or None,
        }, ensure_ascii=False)
        messages.append({
            'role': 'assistant',
            'content': f'{meal.story_text}\n\n```json\n{json_block}\n```',
        })

    # Current meal request
    label = MEAL_LABELS.get(meal_type, meal_type)
    equipment_list = story.get_equipment_list()
    eq_str = '、'.join(equipment_list) if equipment_list else '无'

    prompt = (
        f'我{label}吃了: {food_input}。\n'
        f'当前属性——生命:{story.health}, 敏捷:{story.sanity}, 力量:{story.strength}。\n'
        f'已有装备: {eq_str}。\n'
        f'请只根据「{food_input}」生成内容，不要添加其他食物。\n'
        f'严格按照用餐格式输出：装备（用【】包裹装备名）+ 药水 + 状态 + 属性变化行 + 可选检定。\n'
        f'末尾输出JSON数据块。'
    )

    if meal_type == 'dinner':
        prompt += (
            '\n\n这是今天的最后一餐。输出完本餐装备/药水/状态/属性后，'
            '先用 "=== 冒险结局 ===" 分隔，然后按结局格式输出：'
            '一段结局描述（50-80字）+ 恭喜获得结局【结局名称】！'
            '最后再输出JSON数据块。'
        )

    messages.append({'role': 'user', 'content': prompt})
    return messages


def stream_ai_response(messages):
    """Generator that yields SSE events from AI response.

    Yields tuples of (event_type, data_dict).
    After the generator completes, the caller can access full_text via
    the generator's return value.
    """
    client = get_ai_client()
    model = current_app.config['AI_MODEL']
    extra_body = {
        'enable_thinking': current_app.config['AI_ENABLE_THINKING'],
        'thinking_budget': current_app.config['AI_THINKING_BUDGET'],
    }

    full_text = ''
    thinking_notified = False
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            extra_body=extra_body,
        )

        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            # During thinking phase, send a one-time notification
            reasoning = getattr(delta, 'reasoning_content', None)
            if reasoning:
                if not thinking_notified:
                    thinking_notified = True
                    yield ('thinking', {'type': 'thinking'})
                continue
            content = delta.content
            if content:
                full_text += content
                yield ('text', {'type': 'text', 'content': content})

    except Exception as e:
        yield ('error', {'type': 'error', 'message': str(e)})
        return full_text

    return full_text


def parse_ai_response(full_text):
    """Extract JSON data block and story text from AI response."""
    result = {
        'health_change': 0,
        'sanity_change': 0,
        'strength_change': 0,
        'equipment': None,
        'potion': None,
    }

    # Extract JSON block
    match = re.search(r'```json\s*(.*?)\s*```', full_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            result['health_change'] = max(-30, min(30, int(data.get('health_change', 0))))
            result['sanity_change'] = max(-30, min(30, int(data.get('sanity_change', 0))))
            result['strength_change'] = max(-30, min(30, int(data.get('strength_change', 0))))
            equipment = data.get('equipment')
            if equipment and equipment != 'null' and str(equipment).lower() != 'none':
                eq_name = str(equipment).strip('【】「」')
                result['equipment'] = eq_name
            potion = data.get('potion')
            if potion and potion != 'null' and str(potion).lower() != 'none':
                pt_name = str(potion).strip('【】「」')
                result['potion'] = pt_name
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Extract story text (everything before the JSON block)
    story_text = full_text
    if match:
        story_text = full_text[:match.start()].strip()

    # Handle dinner ending
    ending_text = ''
    if '=== 冒险结局 ===' in story_text:
        parts = story_text.split('=== 冒险结局 ===', 1)
        story_text = parts[0].strip()
        ending_text = parts[1].strip() if len(parts) > 1 else ''

    return {
        'story_text': story_text,
        'ending_text': ending_text,
        **result,
    }


def clamp_stat(value, change):
    """Apply change to a stat value, clamping to 0-200."""
    return max(0, min(200, value + change))
