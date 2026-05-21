"""
认证蓝图 - 用户登录/注册/登出
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        if request.method == 'GET':
            return redirect(url_for('index'))
        if request.is_json:
            return jsonify({
                'message': '已登录',
                'user': current_user.to_dict()
            })

    if request.method == 'GET':
        return render_template('auth/login.html')
    
    # POST: 处理登录
    data = request.get_json() or request.form
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = data.get('remember', False)
    
    if not email or not password:
        if request.is_json:
            return jsonify({'error': '邮箱和密码不能为空'}), 400
        flash('邮箱和密码不能为空', 'error')
        return redirect(url_for('auth.login'))
    
    # 查找用户
    user = User.query.filter_by(email=email, is_deleted=False).first()
    
    if user and user.check_password(password):
        if not user.is_active:
            if request.is_json:
                return jsonify({'error': '账户已被禁用'}), 403
            flash('账户已被禁用', 'error')
            return redirect(url_for('auth.login'))
        
        # 登录成功
        login_user(user, remember=remember)
        if request.is_json:
            return jsonify({
                'message': '登录成功',
                'user': user.to_dict()
            })
        return redirect(url_for('index'))
    
    # 登录失败
    if request.is_json:
        return jsonify({'error': '邮箱或密码错误'}), 401
    flash('邮箱或密码错误', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        if request.method == 'GET':
            return redirect(url_for('index'))
        if request.is_json:
            return jsonify({
                'message': '已登录',
                'user': current_user.to_dict()
            })

    if request.method == 'GET':
        return render_template('auth/register.html')

    data = request.get_json() or request.form
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    errors = []
    if not username or len(username) < 2:
        errors.append('用户名至少 2 个字符')
    if not email or '@' not in email:
        errors.append('请输入有效的邮箱地址')
    if len(password) < 6:
        errors.append('密码至少 6 个字符')
    if password != confirm_password:
        errors.append('两次输入的密码不一致')
    if User.query.filter_by(username=username).first():
        errors.append('用户名已被使用')
    if User.query.filter_by(email=email).first():
        errors.append('邮箱已被注册')

    if errors:
        if request.is_json:
            return jsonify({'error': errors[0]}), 400
        for err in errors:
            flash(err, 'error')
        return redirect(url_for('auth.register'))

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)

    if request.is_json:
        return jsonify({'message': '注册成功', 'user': user.to_dict()}), 201
    flash('注册成功，欢迎！', 'success')
    return redirect(url_for('index'))


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    logout_user()
    if request.is_json:
        return jsonify({'message': '登出成功'})
    flash('已退出登录', 'info')
    return redirect(url_for('index'))


@auth_bp.route('/me')
@login_required
def current():
    """获取当前用户信息"""
    return jsonify({'user': current_user.to_dict()})


@auth_bp.route('/check')
def check():
    """检查登录状态"""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': current_user.to_dict()})
    return jsonify({'authenticated': False})
