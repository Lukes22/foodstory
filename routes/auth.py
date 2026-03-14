from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('story.today'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'error')
            return render_template('auth/login.html')

        login_user(user)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('story.today'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('story.today'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('auth/register.html')

        if len(username) < 2 or len(username) > 20:
            flash('用户名长度需在2-20个字符之间', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('密码长度至少6个字符', 'error')
            return render_template('auth/register.html')

        if password != confirm:
            flash('两次密码输入不一致', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('该用户名已被注册', 'error')
            return render_template('auth/register.html')

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('story.today'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
