import json
import re

from openai import OpenAI
from flask import current_app


def get_ai_client():
    return OpenAI(
        base_url=current_app.config['AI_BASE_URL'],
        api_key=current_app.config['AI_API_KEY'],
    )


SYSTEM_PROMPT = """你是一个RPG游戏系统"食友记副本引擎"。你把玩家每餐吃的食物转化为RPG装备、药水和状态效果。

重要限制:
- 只根据玩家当前输入的食物生成装备和效果，绝对不要自己编造额外的食物、饮料或道具
- 开场白只输出副本信息和Boss信息，不提及任何具体食物，不生成装备或属性变化
- 每餐只处理玩家输入的食物，不要凭空添加其他食物内容
- 装备名称必须直接与玩家输入的食物相关，体现食物特征（如肉包子→盾牌，豆浆→药水）
- 检定时必须严格对比玩家当前属性值，属性值>=检定值才成功，否则失败，不要随意判定
- 不健康食物（高油高糖、暴饮暴食、垃圾食品、方便面、炸鸡、奶茶、烧烤、可乐、薯片等）必须给予负面属性变化，至少一项属性为负值（如【生命-10】【敏捷-5】），绝对不能全部给正值
- 健康食物（蔬菜、水果、均衡搭配、粗粮、牛奶、鸡蛋等）应给予正面属性变化
- 食物健康程度直接决定属性变化方向：越不健康负值越大，越健康正值越大

核心风格:
- 幽默、略带自嘲和毒舌，像吐槽型游戏系统提示
- 装备和药水要有具体数值感，效果描述要结合食物的真实营养特性
- 食物越健康，装备品质越高；垃圾食品给负面装备或debuff
- 语言简洁，像游戏提示框，不要写长篇叙事

===== 开场白格式 =====
当用户请求开场白时，严格按以下格式输出:
【副本名称】（一个有趣的副本标题，如"食堂生存战""外卖迷宫""早八噩梦"等）
【副本背景】（一句话描述今天的日常场景，用RPG语言，30-50字）
【副本等级】（根据日期/星期随机：普通/困难/噩梦/地狱）
【当前身份】（一个幽默的RPG化身份标签，如"负重前行的早八员工""被ddl追杀的勇者"）
【副本Boss】（Boss名称 —— 一句话描述，如"泡面魔王 —— 三天没吃蔬菜的具象化恐惧"）

然后在末尾输出JSON数据块，用 ```json 和 ``` 包裹:
```json
{
  "boss_name": "Boss名称（不含描述部分）",
  "boss_health": 数字,
  "boss_sanity": 数字,
  "boss_strength": 数字
}
```
Boss属性范围100-170，根据副本等级调整：普通100-120，困难115-135，噩梦130-155，地狱145-170。

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
  "carbs": 碳水化合物克数(整数),
  "fat": 脂肪克数(整数),
  "protein": 蛋白质克数(整数),
  "equipment": "装备名（不含【】）",
  "potion": "药水名（不含【】）"
}
```

===== 营养估算规则 =====
- 你必须根据玩家输入的食物，合理估算该餐的碳水化合物、脂肪、蛋白质总克数
- 估算要基于常见食物的真实营养成分（如一碗米饭约60g碳水，一个鸡蛋约6g蛋白质7g脂肪）
- JSON中只需输出 carbs/fat/protein 三个营养素数值，不需要输出 health_change 等属性变化
- 系统会根据营养值自动计算属性变化，你在正文中写的【生命+X】数值仅供参考，会被系统覆盖
- equipment和potion字段必须有值，不能为null

===== 结局格式 =====
当晚餐结束后，在正常用餐内容之后，用 "=== 冒险结局 ===" 分隔，然后输出:
（一段50-80字的最终结局描述。如果今天整体饮食健康均衡，给出正向结局；如果整体不健康或营养不均，给出负向结局。结局必须明确是正向或负向。）
恭喜获得结局【结局名称】！

属性规则:
- 每项属性变化范围: -30 ~ +30
- 生命/敏捷/力量的值范围是0到200
- 属性变化由系统根据营养值自动计算，正文中的【生命+X】仅供展示参考
- JSON中的equipment必须与正文中装备【装备名】完全一致
- JSON中的potion必须与正文中药水【药水名】完全一致
- 用中文回答"""

MEAL_LABELS = {
    'breakfast': '早餐',
    'lunch': '午餐',
    'dinner': '晚餐',
}

# 中国居民膳食指南 2022: 每餐推荐营养素范围 (克)
# 基于 2000kcal/天, 碳水50-65%, 脂肪20-30%, 蛋白质10-15%
# 三餐比例: 早餐30%, 午餐40%, 晚餐30%
NUTRITION_RANGES = {
    'breakfast': {'carbs': (75, 100), 'fat': (13, 20), 'protein': (15, 23)},
    'lunch':     {'carbs': (100, 130), 'fat': (18, 27), 'protein': (20, 30)},
    'dinner':    {'carbs': (75, 100), 'fat': (13, 20), 'protein': (15, 23)},
}


def nutrition_to_change(actual, low, high):
    """Calculate attribute change from a single nutrient vs recommended range.

    Returns int in [-25, +20]. Caller should clamp to [-30, +30].
    """
    mid = (low + high) / 2
    half = (high - low) / 2
    if low <= actual <= high:
        closeness = 1 - abs(actual - mid) / half if half > 0 else 1
        return round(5 + 15 * closeness)
    elif actual < low:
        deficit = (low - actual) / mid if mid > 0 else 1
        return -round(25 * min(deficit, 1.0))
    else:
        excess = (actual - high) / mid if mid > 0 else 1
        return -round(25 * min(excess, 1.0))


def calculate_nutrition_attributes(meal_type, carbs, fat, protein):
    """Calculate attribute changes from nutrition values for a given meal."""
    ranges = NUTRITION_RANGES.get(meal_type, NUTRITION_RANGES['lunch'])
    return {
        'health_change': max(-30, min(30, nutrition_to_change(
            carbs, *ranges['carbs']))),
        'sanity_change': max(-30, min(30, nutrition_to_change(
            fat, *ranges['fat']))),
        'strength_change': max(-30, min(30, nutrition_to_change(
            protein, *ranges['protein']))),
    }


def patch_story_text_attributes(story_text, health_change, sanity_change,
                                strength_change):
    """Replace attribute bracket values in story text with calculated values."""
    def fmt(val):
        return f'+{val}' if val >= 0 else str(val)

    text = story_text
    text = re.sub(r'【生命[+\-]\d+】', f'【生命{fmt(health_change)}】', text)
    text = re.sub(r'【敏捷[+\-]\d+】', f'【敏捷{fmt(sanity_change)}】', text)
    text = re.sub(r'【力量[+\-]\d+】', f'【力量{fmt(strength_change)}】', text)

    # If no attribute line exists, append one
    if '【生命' not in text:
        attr_line = (f'\n\n【生命{fmt(health_change)}】'
                     f'【敏捷{fmt(sanity_change)}】'
                     f'【力量{fmt(strength_change)}】')
        text += attr_line

    return text


def build_opening_messages(date_str):
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {
            'role': 'user',
            'content': (
                f'今天是{date_str}，请生成今日副本开场白。'
                '严格按照开场白格式输出：【副本名称】【副本背景】【副本等级】【当前身份】【副本Boss】五行。'
                '然后在末尾输出JSON数据块，包含Boss的属性数据。'
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
        # Reconstruct assistant response with nutrition JSON block
        json_data = {
            'equipment': meal.equipment_gained or None,
            'potion': getattr(meal, 'potion_gained', None) or None,
        }
        if hasattr(meal, 'carbs') and meal.carbs is not None:
            json_data['carbs'] = meal.carbs
            json_data['fat'] = meal.fat
            json_data['protein'] = meal.protein
        else:
            json_data['carbs'] = 0
            json_data['fat'] = 0
            json_data['protein'] = 0
        json_block = json.dumps(json_data, ensure_ascii=False)
        messages.append({
            'role': 'assistant',
            'content': f'{meal.story_text}\n\n```json\n{json_block}\n```',
        })

    # Current meal request
    label = MEAL_LABELS.get(meal_type, meal_type)
    equipment_list = story.get_equipment_list()
    eq_str = '、'.join(equipment_list) if equipment_list else '无'

    ranges = NUTRITION_RANGES.get(meal_type, NUTRITION_RANGES['lunch'])
    prompt = (
        f'我{label}吃了: {food_input}。\n'
        f'当前属性——生命:{story.health}, 敏捷:{story.sanity}, 力量:{story.strength}。\n'
        f'已有装备: {eq_str}。\n'
        f'本餐推荐营养范围——碳水:{ranges["carbs"][0]}-{ranges["carbs"][1]}g, '
        f'脂肪:{ranges["fat"][0]}-{ranges["fat"][1]}g, '
        f'蛋白质:{ranges["protein"][0]}-{ranges["protein"][1]}g。\n'
        f'请只根据「{food_input}」生成内容，不要添加其他食物。\n'
        f'严格按照用餐格式输出：装备（用【】包裹装备名）+ 药水 + 状态 + 属性变化行 + 可选检定。\n'
        f'末尾输出JSON数据块（包含carbs/fat/protein营养估算和equipment/potion）。'
    )

    if meal_type == 'dinner':
        boss_name = story.boss_name or '未知Boss'
        prompt += (
            f'\n\n这是今天的最后一餐。副本Boss「{boss_name}」正在等待挑战！'
            '输出完本餐装备/药水/状态/属性后，'
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
    """Extract JSON data block and story text from AI response.

    Extracts nutrition values (carbs, fat, protein) from JSON for attribute
    calculation. Attribute brackets in text are kept as fallback if nutrition
    data is missing.
    """
    result = {
        'health_change': 0,
        'sanity_change': 0,
        'strength_change': 0,
        'equipment': None,
        'potion': None,
        'carbs': None,
        'fat': None,
        'protein': None,
    }

    # ---- Step 1: Parse from text brackets (fallback for attributes) ----
    text_health = re.search(r'【生命([+\-]\d+)】', full_text)
    text_sanity = re.search(r'【敏捷([+\-]\d+)】', full_text)
    text_strength = re.search(r'【力量([+\-]\d+)】', full_text)

    if text_health:
        result['health_change'] = max(-30, min(30, int(text_health.group(1))))
    if text_sanity:
        result['sanity_change'] = max(-30, min(30, int(text_sanity.group(1))))
    if text_strength:
        result['strength_change'] = max(-30, min(30, int(text_strength.group(1))))

    # Equipment name from 装备【X】 or 获得装备【X】
    text_equip = re.search(r'装备【([^】]+)】', full_text)
    if text_equip:
        result['equipment'] = text_equip.group(1).strip()

    # Potion name from 药水【X】 or 获得药水【X】
    text_potion = re.search(r'药水【([^】]+)】', full_text)
    if text_potion:
        result['potion'] = text_potion.group(1).strip()

    # ---- Step 2: Parse JSON block ----
    match = re.search(r'```json\s*(.*?)\s*```', full_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            # Extract nutrition values
            if 'carbs' in data and data['carbs'] is not None:
                result['carbs'] = max(0, float(data['carbs']))
            if 'fat' in data and data['fat'] is not None:
                result['fat'] = max(0, float(data['fat']))
            if 'protein' in data and data['protein'] is not None:
                result['protein'] = max(0, float(data['protein']))

            # Equipment/potion fallback from JSON
            if not result['equipment']:
                equipment = data.get('equipment')
                if equipment and equipment != 'null' and str(equipment).lower() != 'none':
                    result['equipment'] = str(equipment).strip('【】「」')
            if not result['potion']:
                potion = data.get('potion')
                if potion and potion != 'null' and str(potion).lower() != 'none':
                    result['potion'] = str(potion).strip('【】「」')

            # Attribute fallback from JSON (only if no nutrition AND no text brackets)
            if result['carbs'] is None:
                if not text_health:
                    result['health_change'] = max(-30, min(30, int(data.get('health_change', 0))))
                if not text_sanity:
                    result['sanity_change'] = max(-30, min(30, int(data.get('sanity_change', 0))))
                if not text_strength:
                    result['strength_change'] = max(-30, min(30, int(data.get('strength_change', 0))))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # ---- Step 3: Extract clean story text ----
    story_text = full_text
    if match:
        story_text = full_text[:match.start()].strip()

    # Handle dinner ending - flexible separator matching
    ending_text = ''
    sep_match = re.search(r'[=＝]{2,}\s*冒险结局\s*[=＝]{2,}', story_text)
    if sep_match:
        ending_text = story_text[sep_match.end():].strip()
        story_text = story_text[:sep_match.start()].strip()
    elif '冒险结局' in story_text:
        parts = story_text.split('冒险结局', 1)
        candidate = parts[1].strip() if len(parts) > 1 else ''
        if candidate:
            ending_text = candidate
            story_text = parts[0].strip().rstrip('=＝ \n')
    else:
        end_match = re.search(
            r'((?:^|\n).*恭喜获得结局【[^】]+】[！!]?\s*)$',
            story_text, re.DOTALL
        )
        if end_match:
            ending_text = end_match.group(1).strip()
            story_text = story_text[:end_match.start()].strip()

    return {
        'story_text': story_text,
        'ending_text': ending_text,
        **result,
    }


def clamp_stat(value, change):
    """Apply change to a stat value, clamping to 0-200."""
    return max(0, min(200, value + change))


def parse_opening_response(full_text):
    """Extract boss data from opening response and return clean text."""
    boss = {
        'boss_name': '',
        'boss_health': 100,
        'boss_sanity': 100,
        'boss_strength': 100,
    }

    # Try to extract boss name from text as fallback
    boss_match = re.search(r'【副本Boss】(.+)', full_text)
    if boss_match:
        boss_line = boss_match.group(1).strip()
        boss_name_part = re.split(r'[——\-\—]', boss_line)[0].strip()
        boss['boss_name'] = boss_name_part

    # Extract JSON block (overrides text extraction for boss_name)
    match = re.search(r'```json\s*(.*?)\s*```', full_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if data.get('boss_name'):
                boss['boss_name'] = str(data['boss_name']).strip('【】「」')
            boss['boss_health'] = max(50, min(200, int(data.get('boss_health', 100))))
            boss['boss_sanity'] = max(50, min(200, int(data.get('boss_sanity', 100))))
            boss['boss_strength'] = max(50, min(200, int(data.get('boss_strength', 100))))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Clean text: remove JSON block
    clean_text = full_text
    if match:
        clean_text = full_text[:match.start()].strip()

    return clean_text, boss
