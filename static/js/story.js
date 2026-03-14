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

        // Show boss info bar if boss exists
        if (data.boss_name) {
            appendBossBar(data);
        }

        // Render past meals
        for (const meal of data.meals) {
            const icon = MEAL_ICONS[meal.meal_type] || '';
            const label = meal.meal_label || meal.meal_type;
            const nutrition = (meal.carbs != null && meal.nutrition_ranges)
                ? { carbs: meal.carbs, fat: meal.fat, protein: meal.protein,
                    nutrition_ranges: meal.nutrition_ranges }
                : null;
            appendStorySection(
                meal.meal_type,
                `${icon} ${label}: ${meal.food_input}`,
                meal.story_text,
                {
                    health_change: meal.health_change,
                    sanity_change: meal.sanity_change,
                    strength_change: meal.strength_change,
                    equipment: meal.equipment_gained,
                },
                nutrition
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
            // Auto-show ending card on page load when adventure is complete
            if (data.boss_name) {
                setTimeout(() => showEndingCard(data), 500);
            }
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

function appendBossBar(data) {
    const storyContent = document.getElementById('story-content');
    const bar = document.createElement('div');
    bar.className = 'boss-bar';
    bar.innerHTML =
        `<span class="boss-bar-icon">\u{1F47E}</span> ` +
        `<span class="boss-bar-name">Boss: ${escapeHtml(data.boss_name)}</span>` +
        `<span class="boss-bar-stats">` +
        `\u2764${data.boss_health} \u26A1${data.boss_sanity} \u2694${data.boss_strength}` +
        `</span>`;
    storyContent.appendChild(bar);
}

function appendStorySection(id, header, text, changes, nutrition) {
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

    if (nutrition) {
        html += renderNutritionCard(nutrition);
    }

    section.innerHTML = html;
    storyContent.appendChild(section);
}

function renderNutritionCard(data) {
    if (data.carbs == null || !data.nutrition_ranges) return '';

    const rows = [
        { label: '\u{1F33E} \u78B3\u6C34', actual: data.carbs, range: data.nutrition_ranges.carbs },
        { label: '\u{1F9C8} \u8102\u80AA', actual: data.fat, range: data.nutrition_ranges.fat },
        { label: '\u{1F969} \u86CB\u767D\u8D28', actual: data.protein, range: data.nutrition_ranges.protein },
    ];

    let html = '<div class="nutrition-card"><div class="nutrition-title">\u2697\uFE0F \u8425\u517B\u5206\u6790</div>';
    for (const row of rows) {
        const [low, high] = row.range;
        const actual = Math.round(row.actual);
        const inRange = actual >= low && actual <= high;
        const statusCls = inRange ? 'in-range' : 'out-range';
        const statusIcon = inRange ? '\u2714' : '\u2718';

        // Progress bar: map actual to visual position
        // Bar represents 0 to high*2, with recommended zone highlighted
        const barMax = high * 2;
        const fillPct = Math.min(100, (actual / barMax) * 100);
        const zoneLPct = (low / barMax) * 100;
        const zoneWPct = ((high - low) / barMax) * 100;

        html += `<div class="nutrition-row">` +
            `<span class="nutrition-label">${row.label}</span>` +
            `<span class="nutrition-value ${statusCls}">${actual}g</span>` +
            `<div class="nutrition-bar">` +
            `<div class="nutrition-bar-zone" style="left:${zoneLPct}%;width:${zoneWPct}%"></div>` +
            `<div class="nutrition-bar-fill ${statusCls}" style="width:${fillPct}%"></div>` +
            `</div>` +
            `<span class="nutrition-range">${low}-${high}g</span>` +
            `<span class="nutrition-status ${statusCls}">${statusIcon}</span>` +
            `</div>`;
    }
    html += '</div>';
    return html;
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

// ===== Ending Card =====

function showEndingCard(data) {
    const overlay = document.getElementById('ending-overlay');
    if (!overlay) return;

    // Title - extract dungeon name
    let title = '\u526F\u672C\u7ED3\u7B97';
    const openText = data.opening_text || '';
    const tm = openText.match(/【副本名称】(.+)/);
    if (tm) title = tm[1].trim();
    document.getElementById('ending-card-title').textContent = title;

    // Boss info
    const bossEl = document.getElementById('ending-card-boss');
    if (data.boss_name) {
        bossEl.textContent = '\u{1F47E} Boss: ' + data.boss_name;
        bossEl.style.display = 'block';
    } else {
        bossEl.style.display = 'none';
    }

    // Stat comparison
    const compEl = document.getElementById('ending-card-comparison');
    const healthWin = data.health >= (data.boss_health || 100);
    const sanityWin = data.sanity >= (data.boss_sanity || 100);
    const strengthWin = data.strength >= (data.boss_strength || 100);
    const wins = [healthWin, sanityWin, strengthWin].filter(Boolean).length;
    // Use backend victory if available, else calculate locally
    const victory = data.victory !== undefined && data.victory !== null
        ? data.victory
        : wins >= 2;

    compEl.innerHTML =
        buildStatCompare('\u2764', '\u751F\u547D', data.health, data.boss_health || 100, healthWin) +
        buildStatCompare('\u26A1', '\u654F\u6377', data.sanity, data.boss_sanity || 100, sanityWin) +
        buildStatCompare('\u2694', '\u529B\u91CF', data.strength, data.boss_strength || 100, strengthWin);

    // Result
    const resultEl = document.getElementById('ending-card-result');
    const scoreGain = data.score_gain || (victory ? 10 : 3);
    if (victory) {
        resultEl.innerHTML = '\u2694 \u526F\u672C\u6311\u6218\u6210\u529F \u2694' +
            `<div class="ending-card-score">+${scoreGain} \u79EF\u5206</div>`;
        resultEl.className = 'ending-card-result victory';
    } else {
        resultEl.innerHTML = '\u{1F480} \u526F\u672C\u6311\u6218\u5931\u8D25 \u{1F480}' +
            `<div class="ending-card-score">+${scoreGain} \u79EF\u5206</div>`;
        resultEl.className = 'ending-card-result defeat';
    }

    // Ending text
    const textEl = document.getElementById('ending-card-text');
    if (data.ending_text) {
        textEl.innerHTML = highlightBrackets(data.ending_text);
        textEl.style.display = 'block';
    } else {
        textEl.style.display = 'none';
    }

    overlay.style.display = 'flex';
}

function buildStatCompare(icon, label, playerVal, bossVal, win) {
    const cls = win ? 'win' : 'lose';
    return `<div class="stat-compare ${cls}">` +
        `<div class="stat-compare-icon">${icon}</div>` +
        `<div class="stat-compare-label">${label}</div>` +
        `<div class="stat-compare-values">${playerVal} vs ${bossVal}</div>` +
        `<div class="stat-compare-mark">${win ? '\u2714' : '\u2718'}</div>` +
        `</div>`;
}

function closeEndingCard(event, force) {
    if (force || event.target.id === 'ending-overlay') {
        document.getElementById('ending-overlay').style.display = 'none';
    }
}

function viewEndingCard() {
    if (currentState && currentState.is_complete) {
        showEndingCard(currentState);
    }
}

// ===== Adventure Start =====

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
                        // Reload status to get clean text + boss info
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

// ===== Meal Submission =====

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
                        // Replace streamed text with clean parsed story_text
                        if (event.story_text) {
                            textEl.innerHTML = highlightBrackets(event.story_text);
                        } else {
                            textEl.innerHTML = highlightBrackets(textEl.textContent);
                        }

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

                        // Append nutrition card if available
                        if (event.carbs != null && event.nutrition_ranges) {
                            const nutritionHtml = renderNutritionCard({
                                carbs: event.carbs,
                                fat: event.fat,
                                protein: event.protein,
                                nutrition_ranges: event.nutrition_ranges,
                            });
                            if (nutritionHtml) {
                                const nutritionDiv = document.createElement('div');
                                nutritionDiv.innerHTML = nutritionHtml;
                                section.appendChild(nutritionDiv.firstElementChild);
                            }
                        }

                        // Show ending card if dinner (check mealType)
                        if (mealType === 'dinner') {
                            if (event.ending_text) {
                                appendEnding(event.ending_text);
                            }
                            scrollStoryToBottom();

                            // Show ending card with boss comparison after a brief delay
                            setTimeout(() => {
                                showEndingCard({
                                    opening_text: currentState ? currentState.opening_text : '',
                                    boss_name: currentState ? currentState.boss_name : '',
                                    boss_health: currentState ? currentState.boss_health : 100,
                                    boss_sanity: currentState ? currentState.boss_sanity : 100,
                                    boss_strength: currentState ? currentState.boss_strength : 100,
                                    health: event.new_health,
                                    sanity: event.new_sanity,
                                    strength: event.new_strength,
                                    ending_text: event.ending_text || '',
                                    victory: event.victory,
                                    score_gain: event.score_gain,
                                });
                            }, 800);
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
    // Highlight opening labels: 【副本名称】【副本背景】【副本等级】【当前身份】【副本Boss】
    html = html.replace(/【(副本名称|副本背景|副本等级|当前身份|副本Boss)】/g,
        '<span class="bracket-label">【$1】</span>');
    // Highlight remaining 【...】 (equipment, potion, status, ending names etc.)
    html = html.replace(/【([^】]+)】/g, function(match, inner) {
        if (match.includes('bracket-')) return match;
        return '<span class="bracket-misc">【' + inner + '】</span>';
    });
    return html;
}
