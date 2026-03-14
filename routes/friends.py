from datetime import date

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import User, Friendship, DailyStory

friends_bp = Blueprint('friends', __name__, url_prefix='/friends')


@friends_bp.route('/')
@login_required
def index():
    # Accepted friends
    friends = get_accepted_friends(current_user.id)

    # Pending requests received
    pending = Friendship.query.filter_by(
        friend_id=current_user.id, status='pending'
    ).all()

    # Build leaderboard: friends + self
    all_users = friends + [current_user]
    leaderboard = []
    for u in all_users:
        latest = DailyStory.query.filter_by(
            user_id=u.id, is_complete=True
        ).order_by(DailyStory.date.desc()).first()

        attr_total = 0
        if latest:
            attr_total = latest.health + latest.sanity + latest.strength

        leaderboard.append({
            'user_id': u.id,
            'username': u.username,
            'score': u.score if hasattr(u, 'score') else 0,
            'attr_total': attr_total,
            'is_self': u.id == current_user.id,
        })

    leaderboard.sort(key=lambda x: (-x['score'], -x['attr_total']))

    return render_template('friends/list.html',
                           friends=friends, pending=pending,
                           leaderboard=leaderboard)


@friends_bp.route('/add', methods=['POST'])
@login_required
def add():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供数据'}), 400

    username = data.get('username', '').strip()
    if not username:
        return jsonify({'error': '请输入用户名'}), 400

    if username == current_user.username:
        return jsonify({'error': '不能添加自己为好友'}), 400

    friend = User.query.filter_by(username=username).first()
    if not friend:
        return jsonify({'error': '用户不存在'}), 404

    # Check if already friends or pending
    existing = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user.id))
    ).first()

    if existing:
        if existing.status == 'accepted':
            return jsonify({'error': '你们已经是好友了'}), 400
        else:
            return jsonify({'error': '好友请求已发送，请等待对方确认'}), 400

    friendship = Friendship(user_id=current_user.id, friend_id=friend.id)
    db.session.add(friendship)
    db.session.commit()

    return jsonify({'message': f'已向 {username} 发送好友请求'})


@friends_bp.route('/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)

    if friendship.friend_id != current_user.id:
        return jsonify({'error': '无权操作'}), 403

    if friendship.status != 'pending':
        return jsonify({'error': '该请求已处理'}), 400

    friendship.status = 'accepted'
    db.session.commit()

    return jsonify({'message': '已接受好友请求'})


@friends_bp.route('/reject/<int:friendship_id>', methods=['POST'])
@login_required
def reject(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)

    if friendship.friend_id != current_user.id:
        return jsonify({'error': '无权操作'}), 403

    if friendship.status != 'pending':
        return jsonify({'error': '该请求已处理'}), 400

    db.session.delete(friendship)
    db.session.commit()

    return jsonify({'message': '已拒绝好友请求'})


@friends_bp.route('/<int:user_id>/story')
@login_required
def view_story(user_id):
    # Verify friendship
    is_friend = Friendship.query.filter(
        (
            ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user_id)) |
            ((Friendship.user_id == user_id) & (Friendship.friend_id == current_user.id))
        ) & (Friendship.status == 'accepted')
    ).first()

    if not is_friend:
        return render_template('friends/story_view.html', friend=None, story=None,
                               error='你们还不是好友')

    friend = User.query.get_or_404(user_id)
    story = DailyStory.query.filter_by(
        user_id=user_id, date=date.today()
    ).first()

    return render_template('friends/story_view.html', friend=friend, story=story)


def get_accepted_friends(user_id):
    """Get all accepted friends for a user."""
    friendships = Friendship.query.filter(
        (
            ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id))
        ) & (Friendship.status == 'accepted')
    ).all()

    friends = []
    for f in friendships:
        friend_id = f.friend_id if f.user_id == user_id else f.user_id
        user = User.query.get(friend_id)
        if user:
            friends.append(user)
    return friends
