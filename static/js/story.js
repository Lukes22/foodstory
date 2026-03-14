const MEAL_ICONS = {
    breakfast: '\u{1F373}',
    lunch: '\u{1F35C}',
    dinner: '\u{1F356}',
};

const MEAL_LABELS = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
};

const THINKING_OPENING = 'thinking-opening';
const THINKING_MEAL = 'thinking-meal';

function showThinkingOpening(el) {
    el.innerHTML = '<div class="thinking-hint">今日副本抽取中...</div>';
    el.dataset.thinking = THINKING_OPENING;
}

function showThinkingMeal(el) {
    el.innerHTML =
        '<div class="thinking-hint">进食中...' +
        '<div class="progress-bar"><div class="progress-bar-fill"></div></div>' +
        '</div>';
    el.dataset.thinking = THINKING_MEAL;
}

function clearThinking(el) {
    if (el.dataset.thinking) {
        el.innerHTML = '';
        el.textContent = '';
        delete el.dataset.thinking;
    }
}

let currentState = null;

document.addEventListener('DOMContentLoaded', loadStatus);

async function loadStatus() {
    try {
        const resp = await fetch('/story/status');
        const data = await resp.json();
        currentState = data;
        renderState(data);
    } catch (err) {
        console.error('Failed to load status:', err);
    }
}

function renderState(data) {
    updateStats(data.health, data.sanity, data.strength);
    renderEquipment(data.equipment);
    renderPotions(data.potions);

    const storyEmpty = document.getElementById('story-empty');
    const storyContent = document.getElementById('story-content');
    const inputArea = document.getElementById('input-area');
    const completeArea = document.getElementById('complete-area');
    const btnStart = document.getElementById('btn-start');

    // If story has opening, show content
    if (data.opening_text) {
        storyEmpty.style.display = 'none';
        storyContent.style.display = 'block';

        // Render opening - extract dungeon title from text
        storyContent.innerHTML = '';
        let openingHeader = '\u{1F3F0} 今日副本';
        const titleMatch = data.opening_text.match(/【副本名称】(.+)/);
        if (titleMatch) {
            openingHeader = '\u{1F3F0} ' + titleMatch[1].trim();
        }
        appendStorySection('opening', openingHeader, data.opening_text);

        // Render past meals
        for (const meal of data.meals) {
            const icon = MEAL_ICONS[meal.meal_type] || '';
            const label = meal.meal_label || meal.meal_type;
            appendStorySection(
                meal.meal_type,
                `${icon} ${label}: ${meal.food_input}`,
                meal.story_text,
                {
                    health_change: meal.health_change,
                    sanity_change: meal.sanity_change,
                    strength_change: meal.strength_change,
                    equipment: meal.equipment_gained,
                }
            );
        }

        // Render ending if complete
        if (data.is_complete && data.ending_text) {
            appendEnding(data.ending_text);
        }

        // Show input or complete
        if (data.is_complete) {
            inputArea.style.display = 'none';
            completeArea.style.display = 'block';
        } else if (data.next_meal) {
            inputArea.style.display = 'block';
            completeArea.style.display = 'none';
            document.getElementById('input-phase').textContent =
                `${MEAL_ICONS[data.next_meal] || ''} 请输入你的${data.next_meal_label}`;
            document.getElementById('food-input').placeholder =
                `输入你${data.next_meal_label}吃了什么...`;
        }

        scrollStoryToBottom();
    } else {
        // No story yet, show start button
        storyEmpty.style.display = 'flex';
        storyContent.style.display = 'none';
        inputArea.style.display = 'none';
        completeArea.style.display = 'none';
    }
}

function updateStats(health, sanity, strength) {
    document.getElementById('stat-health').textContent = health;
    document.getElementById('stat-sanity').textContent = sanity;
    document.getElementById('stat-strength').textContent = strength;
}

function renderEquipment(equipment) {
    const list = document.getElementById('equipment-list');
    const noEquip = document.getElementById('no-equipment');
    if (!equipment || equipment.length === 0) {
        noEquip.style.display = 'inline';
        // Remove any tags
        list.querySelectorAll('.equipment-tag').forEach(el => el.remove());
    } else {
        noEquip.style.display = 'none';
        list.querySelectorAll('.equipment-tag').forEach(el => el.remove());
        for (const item of equipment) {
            const tag = document.createElement('span');
            tag.className = 'equipment-tag';
            tag.textContent = item;
            list.appendChild(tag);
        }
    }
}

function renderPotions(potions) {
    const list = document.getElementById('potion-list');
    const noPot = document.getElementById('no-potion');
    if (!potions || potions.length === 0) {
        noPot.style.display = 'inline';
        list.querySelectorAll('.equipment-tag').forEach(el => el.remove());
    } else {
        noPot.style.display = 'none';
        list.querySelectorAll('.equipment-tag').forEach(el => el.remove());
        for (const item of potions) {
            const tag = document.createElement('span');
            tag.className = 'equipment-tag potion-tag';
            tag.textContent = item;
            list.appendChild(tag);
        }
    }
}

function addPotionTag(item) {
    const list = document.getElementById('potion-list');
    const noPot = document.getElementById('no-potion');
    noPot.style.display = 'none';

    const tag = document.createElement('span');
    tag.className = 'equipment-tag potion-tag new';
    tag.textContent = item;
    list.appendChild(tag);

    setTimeout(() => tag.classList.remove('new'), 1200);
}

function appendStorySection(id, header, text, changes) {
    const storyContent = document.getElementById('story-content');
    const section = document.createElement('div');
    section.className = 'story-section';
    section.id = `section-${id}`;

    let html = `<div class="story-section-header">${header}</div>`;
    html += `<div class="story-text">${highlightBrackets(text)}</div>`;

    if (changes) {
        html += '<div class="story-changes">';
        if (changes.health_change !== 0) {
            const cls = changes.health_change > 0 ? 'positive' : 'negative';
            const sign = changes.health_change > 0 ? '+' : '';
            html += `<span class="change-item ${cls}">\u2764 ${sign}${changes.health_change}</span>`;
        }
        if (changes.sanity_change !== 0) {
            const cls = changes.sanity_change > 0 ? 'positive' : 'negative';
            const sign = changes.sanity_change > 0 ? '+' : '';
            html += `<span class="change-item ${cls}">\u26A1 ${sign}${changes.sanity_change}</span>`;
        }
        if (changes.strength_change !== 0) {
            const cls = changes.strength_change > 0 ? 'positive' : 'negative';
            const sign = changes.strength_change > 0 ? '+' : '';
            html += `<span class="change-item ${cls}">\u2694 ${sign}${changes.strength_change}</span>`;
        }
        if (changes.equipment) {
            html += `<span class="change-item equipment">\u{1F392} 装备: ${escapeHtml(changes.equipment)}</span>`;
        }
        if (changes.potion_gained) {
            html += `<span class="change-item potion">\u{1F9EA} 药水: ${escapeHtml(changes.potion_gained)}</span>`;
        }
        html += '</div>';
    }

    section.innerHTML = html;
    storyContent.appendChild(section);
}

function appendEnding(text) {
    const storyContent = document.getElementById('story-content');
    const ending = document.createElement('div');
    ending.className = 'story-ending';
    ending.innerHTML = `<h2>\u{1F3C6} \u526F\u672C\u7ED3\u7B97 \u{1F3C6}</h2><div class="story-text">${highlightBrackets(text)}</div>`;
    storyContent.appendChild(ending);
}

function scrollStoryToBottom() {
    const area = document.getElementById('story-area');
    area.scrollTop = area.scrollHeight;
}

async function startAdventure() {
    const btn = document.getElementById('btn-start');
    btn.disabled = true;
    btn.textContent = '冒险开启中...';

    const storyEmpty = document.getElementById('story-empty');
    const storyContent = document.getElementById('story-content');

    storyContent.style.display = 'block';
    storyContent.innerHTML = '';

    // Create opening section with empty text
    appendStorySection('opening', '\u{1F3F0} 今日副本', '');
    const textEl = storyContent.querySelector('#section-opening .story-text');

    try {
        const resp = await fetch('/story/start', { method: 'POST' });

        if (!resp.ok) {
            let errMsg = '请求失败';
            try { const d = await resp.json(); errMsg = d.error || errMsg; } catch(e) {}
            textEl.textContent = '[错误: ' + errMsg + ']';
            btn.disabled = false;
            btn.textContent = '开始今日冒险';
            return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        storyEmpty.style.display = 'none';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const jsonStr = line.slice(6);
                try {
                    const event = JSON.parse(jsonStr);
                    if (event.type === 'thinking') {
                        showThinkingOpening(textEl);
                    } else if (event.type === 'text') {
                        // Clear thinking hint on first real text
                        clearThinking(textEl);
                        textEl.textContent += event.content;
                        scrollStoryToBottom();
                    } else if (event.type === 'done') {
                        // Update section header with dungeon title
                        const fullText = textEl.textContent;
                        const tm = fullText.match(/【副本名称】(.+)/);
                        if (tm) {
                            const headerEl = storyContent.querySelector('#section-opening .story-section-header');
                            if (headerEl) headerEl.textContent = '\u{1F3F0} ' + tm[1].trim();
                        }
                        // Re-render with highlighting
                        textEl.innerHTML = highlightBrackets(fullText);
                        // Reload status to get next meal info
                        await loadStatus();
                    } else if (event.type === 'error') {
                        textEl.textContent += '\n\n[错误: ' + event.message + ']';
                    }
                } catch (e) {
                    // ignore parse errors
                }
            }
        }
    } catch (err) {
        textEl.textContent += '\n\n[连接错误，请刷新重试]';
        console.error(err);
    }

    // Re-enable button in case of failure (if success, renderState hides it)
    btn.disabled = false;
    btn.textContent = '开始今日冒险';
}

async function submitMeal() {
    const input = document.getElementById('food-input');
    const btn = document.getElementById('btn-submit');
    const food = input.value.trim();

    if (!food) return;

    btn.disabled = true;
    input.disabled = true;
    btn.textContent = '故事生成中...';

    const storyContent = document.getElementById('story-content');
    const mealType = currentState ? currentState.next_meal : 'unknown';
    const mealLabel = currentState ? currentState.next_meal_label : '用餐';
    const icon = MEAL_ICONS[mealType] || '';

    // Create new section for streaming
    appendStorySection(mealType, `${icon} ${mealLabel}: ${food}`, '');
    const section = storyContent.querySelector(`#section-${mealType}`);
    const textEl = section.querySelector('.story-text');
    scrollStoryToBottom();

    try {
        const resp = await fetch('/story/meal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ food: food }),
        });

        if (!resp.ok) {
            const errData = await resp.json();
            textEl.textContent = '[错误: ' + (errData.error || '未知错误') + ']';
            btn.disabled = false;
            input.disabled = false;
            btn.textContent = '出发!';
            return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const jsonStr = line.slice(6);
                try {
                    const event = JSON.parse(jsonStr);
                    if (event.type === 'thinking') {
                        showThinkingMeal(textEl);
                        scrollStoryToBottom();
                    } else if (event.type === 'text') {
                        clearThinking(textEl);
                        textEl.textContent += event.content;
                        scrollStoryToBottom();
                    } else if (event.type === 'result') {
                        // Re-render story text with bracket highlighting
                        textEl.innerHTML = highlightBrackets(textEl.textContent);

                        animateStatChange('health', event.health_change, event.new_health);
                        animateStatChange('sanity', event.sanity_change, event.new_sanity);
                        animateStatChange('strength', event.strength_change, event.new_strength);

                        // Show changes under story
                        const changes = document.createElement('div');
                        changes.className = 'story-changes';
                        let changesHtml = '';
                        if (event.health_change !== 0) {
                            const cls = event.health_change > 0 ? 'positive' : 'negative';
                            const sign = event.health_change > 0 ? '+' : '';
                            changesHtml += `<span class="change-item ${cls}">\u2764 ${sign}${event.health_change}</span>`;
                        }
                        if (event.sanity_change !== 0) {
                            const cls = event.sanity_change > 0 ? 'positive' : 'negative';
                            const sign = event.sanity_change > 0 ? '+' : '';
                            changesHtml += `<span class="change-item ${cls}">\u26A1 ${sign}${event.sanity_change}</span>`;
                        }
                        if (event.strength_change !== 0) {
                            const cls = event.strength_change > 0 ? 'positive' : 'negative';
                            const sign = event.strength_change > 0 ? '+' : '';
                            changesHtml += `<span class="change-item ${cls}">\u2694 ${sign}${event.strength_change}</span>`;
                        }
                        if (event.equipment) {
                            changesHtml += `<span class="change-item equipment">\u{1F392} 装备: ${escapeHtml(event.equipment)}</span>`;
                            addEquipmentTag(event.equipment);
                        }
                        if (event.potion) {
                            changesHtml += `<span class="change-item potion">\u{1F9EA} 药水: ${escapeHtml(event.potion)}</span>`;
                            addPotionTag(event.potion);
                        }
                        changes.innerHTML = changesHtml;
                        section.appendChild(changes);

                        // Show ending if dinner
                        if (event.ending_text) {
                            appendEnding(event.ending_text);
                        }

                        scrollStoryToBottom();
                    } else if (event.type === 'done') {
                        await loadStatus();
                    } else if (event.type === 'error') {
                        textEl.textContent += '\n\n[错误: ' + event.message + ']';
                    }
                } catch (e) {
                    // ignore
                }
            }
        }
    } catch (err) {
        textEl.textContent += '\n\n[连接错误，请刷新重试]';
        console.error(err);
    }

    input.value = '';
    btn.disabled = false;
    input.disabled = false;
    btn.textContent = '出发!';
}

function animateStatChange(stat, change, newValue) {
    const valueEl = document.getElementById(`stat-${stat}`);
    const changeEl = document.getElementById(`change-${stat}`);

    if (change === 0) return;

    // Update value
    valueEl.textContent = newValue;

    // Show change indicator
    const sign = change > 0 ? '+' : '';
    changeEl.textContent = `${sign}${change}`;
    changeEl.className = `stat-change show ${change > 0 ? 'positive' : 'negative'}`;

    // Animate
    valueEl.classList.add(change > 0 ? 'animate-up' : 'animate-down');

    setTimeout(() => {
        valueEl.classList.remove('animate-up', 'animate-down');
    }, 600);

    setTimeout(() => {
        changeEl.classList.remove('show');
    }, 2000);
}

function addEquipmentTag(item) {
    const list = document.getElementById('equipment-list');
    const noEquip = document.getElementById('no-equipment');
    noEquip.style.display = 'none';

    const tag = document.createElement('span');
    tag.className = 'equipment-tag new';
    tag.textContent = item;
    list.appendChild(tag);

    setTimeout(() => tag.classList.remove('new'), 1200);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function highlightBrackets(text) {
    // Escape HTML first, then highlight bracketed content
    let html = escapeHtml(text);
    // Highlight stat changes like 【生命+15】【敏捷-5】【力量+20】
    html = html.replace(/【((?:生命|敏捷|力量)[+\-]\d+)】/g,
        '<span class="bracket-stat">【$1】</span>');
    // Highlight checks like 【检定：敏捷>60，成功！】
    html = html.replace(/【(检定[^】]+)】/g,
        '<span class="bracket-check">【$1】</span>');
    // Highlight opening labels: 【副本背景】【副本等级】【当前身份】
    html = html.replace(/【(副本背景|副本等级|当前身份)】/g,
        '<span class="bracket-label">【$1】</span>');
    // Highlight remaining 【...】 (equipment, potion, status, ending names etc.)
    html = html.replace(/【([^】]+)】/g, function(match, inner) {
        if (match.includes('bracket-')) return match;
        return '<span class="bracket-misc">【' + inner + '】</span>';
    });
    return html;
}
