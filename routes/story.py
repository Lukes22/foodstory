import json
from datetime import date

from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user

from extensions import db
from models import DailyStory, MealEntry, User
from ai_service import (
    build_opening_messages, build_meal_messages,
    stream_ai_response, parse_ai_response, parse_opening_response, clamp_stat,
    calculate_nutrition_attributes, patch_story_text_attributes, NUTRITION_RANGES,
)

story_bp = Blueprint('story', __name__, url_prefix='/story')

PHASE_MEAL_MAP = {0: 'breakfast', 1: 'lunch', 2: 'dinner'}
MEAL_LABELS = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐'}


def get_or_create_today_story():
    today = date.today()
    story = DailyStory.query.filter_by(
        user_id=current_user.id, date=today
    ).first()
    if not story:
        story = DailyStory(user_id=current_user.id, date=today)
        db.session.add(story)
        db.session.commit()
    return story


def sse_format(data):
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@story_bp.route('/today')
@login_required
def today():
    story = get_or_create_today_story()
    return render_template('story/daily.html', story=story)


@story_bp.route('/status')
@login_required
def status():
    story = get_or_create_today_story()
    meals = []
    for m in story.meals.all():
        meal_data = {
            'meal_type': m.meal_type,
            'meal_label': MEAL_LABELS.get(m.meal_type, m.meal_type),
            'food_input': m.food_input,
            'story_text': m.story_text,
            'health_change': m.health_change,
            'sanity_change': m.sanity_change,
            'strength_change': m.strength_change,
            'equipment_gained': m.equipment_gained,
            'potion_gained': m.potion_gained,
            'carbs': m.carbs,
            'fat': m.fat,
            'protein': m.protein,
        }
        ranges = NUTRITION_RANGES.get(m.meal_type)
        if ranges:
            meal_data['nutrition_ranges'] = {
                k: list(v) for k, v in ranges.items()
            }
        meals.append(meal_data)

    next_meal = PHASE_MEAL_MAP.get(story.current_phase)
    next_meal_label = MEAL_LABELS.get(next_meal, '') if next_meal else ''

    return jsonify({
        'phase': story.current_phase,
        'is_complete': story.is_complete,
        'victory': story.victory,
        'opening_text': story.opening_text,
        'ending_text': story.ending_text,
        'health': story.health,
        'sanity': story.sanity,
        'strength': story.strength,
        'equipment': story.get_equipment_list(),
        'potions': story.get_potion_list(),
        'boss_name': story.boss_name or '',
        'boss_health': story.boss_health,
        'boss_sanity': story.boss_sanity,
        'boss_strength': story.boss_strength,
        'meals': meals,
        'next_meal': next_meal,
        'next_meal_label': next_meal_label,
    })


@story_bp.route('/start', methods=['POST'])
@login_required
def start():
    story = get_or_create_today_story()

    if story.opening_text:
        return jsonify({'error': '今日冒险已经开始了'}), 400

    date_str = story.date.strftime('%Y年%m月%d日')
    messages = build_opening_messages(date_str)

    def generate():
        collected = []
        has_error = False

        for event_type, data in stream_ai_response(messages):
            if event_type == 'text':
                collected.append(data['content'])
            elif event_type == 'error':
                has_error = True
            yield sse_format(data)

        full_text = ''.join(collected)

        if full_text:
            clean_text, boss_data = parse_opening_response(full_text)
            DailyStory.query.filter_by(id=story.id).update({
                'opening_text': clean_text,
                'boss_name': boss_data['boss_name'],
                'boss_health': boss_data['boss_health'],
                'boss_sanity': boss_data['boss_sanity'],
                'boss_strength': boss_data['boss_strength'],
            })
            db.session.commit()

        yield sse_format({'type': 'done'})

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@story_bp.route('/meal', methods=['POST'])
@login_required
def meal():
    story = get_or_create_today_story()

    if story.is_complete:
        return jsonify({'error': '今日冒险已结束'}), 400

    if not story.opening_text:
        return jsonify({'error': '请先开始今日冒险'}), 400

    expected_meal = PHASE_MEAL_MAP.get(story.current_phase)
    if not expected_meal:
        return jsonify({'error': '今日冒险已结束'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供食物信息'}), 400

    food_input = data.get('food', '').strip()
    if not food_input:
        return jsonify({'error': '请输入你吃了什么'}), 400

    meal_type = expected_meal
    messages = build_meal_messages(story, food_input, meal_type)

    def generate():
        full_text = ''
        has_error = False

        for event_type, evt_data in stream_ai_response(messages):
            if event_type == 'text':
                full_text += evt_data['content']
            elif event_type == 'error':
                has_error = True
            yield sse_format(evt_data)

        if has_error or not full_text:
            yield sse_format({'type': 'done'})
            return

        # Parse AI response
        parsed = parse_ai_response(full_text)

        # Calculate attribute changes from nutrition if available
        carbs = parsed.get('carbs')
        fat = parsed.get('fat')
        protein = parsed.get('protein')

        if carbs is not None and fat is not None and protein is not None:
            attr = calculate_nutrition_attributes(meal_type, carbs, fat, protein)
            parsed['health_change'] = attr['health_change']
            parsed['sanity_change'] = attr['sanity_change']
            parsed['strength_change'] = attr['strength_change']
            parsed['story_text'] = patch_story_text_attributes(
                parsed['story_text'],
                attr['health_change'], attr['sanity_change'],
                attr['strength_change'],
            )

        # Create meal entry
        entry = MealEntry(
            story_id=story.id,
            meal_type=meal_type,
            food_input=food_input,
            story_text=parsed['story_text'],
            health_change=parsed['health_change'],
            sanity_change=parsed['sanity_change'],
            strength_change=parsed['strength_change'],
            equipment_gained=parsed['equipment'] or '',
            potion_gained=parsed['potion'] or '',
            carbs=carbs,
            fat=fat,
            protein=protein,
        )
        db.session.add(entry)
        db.session.flush()

        # Update story via query (ORM attribute changes don't persist in generators)
        new_health = clamp_stat(story.health, parsed['health_change'])
        new_sanity = clamp_stat(story.sanity, parsed['sanity_change'])
        new_strength = clamp_stat(story.strength, parsed['strength_change'])

        equipment_list = story.get_equipment_list()
        if parsed['equipment']:
            equipment_list.append(parsed['equipment'])
        equipment_json = json.dumps(equipment_list, ensure_ascii=False)

        potion_list = story.get_potion_list()
        if parsed['potion']:
            potion_list.append(parsed['potion'])
        potion_json = json.dumps(potion_list, ensure_ascii=False)

        new_phase = story.current_phase + 1
        update_fields = {
            'health': new_health,
            'sanity': new_sanity,
            'strength': new_strength,
            'equipment_summary': equipment_json,
            'potion_summary': potion_json,
            'current_phase': new_phase,
        }

        if meal_type == 'dinner':
            update_fields['ending_text'] = parsed['ending_text']
            update_fields['is_complete'] = True

            # Determine boss fight result
            health_win = new_health >= story.boss_health
            sanity_win = new_sanity >= story.boss_sanity
            strength_win = new_strength >= story.boss_strength
            wins = sum([health_win, sanity_win, strength_win])
            is_victory = wins >= 2
            update_fields['victory'] = is_victory

            # Award score to user
            score_gain = 10 if is_victory else 3
            User.query.filter_by(id=story.user_id).update(
                {'score': User.score + score_gain}
            )

        DailyStory.query.filter_by(id=story.id).update(update_fields)
        db.session.commit()

        # Send result event
        result_data = {
            'type': 'result',
            'health_change': parsed['health_change'],
            'sanity_change': parsed['sanity_change'],
            'strength_change': parsed['strength_change'],
            'equipment': parsed['equipment'],
            'potion': parsed['potion'],
            'new_health': new_health,
            'new_sanity': new_sanity,
            'new_strength': new_strength,
            'story_text': parsed['story_text'],
            'ending_text': parsed['ending_text'],
            'carbs': carbs,
            'fat': fat,
            'protein': protein,
        }
        ranges = NUTRITION_RANGES.get(meal_type)
        if ranges:
            result_data['nutrition_ranges'] = {
                k: list(v) for k, v in ranges.items()
            }
        if meal_type == 'dinner':
            result_data['victory'] = is_victory
            result_data['score_gain'] = score_gain

        yield sse_format(result_data)

        yield sse_format({'type': 'done'})

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@story_bp.route('/history')
@login_required
def history():
    stories = DailyStory.query.filter_by(
        user_id=current_user.id
    ).order_by(DailyStory.date.desc()).all()
    return render_template('story/history.html', stories=stories)
