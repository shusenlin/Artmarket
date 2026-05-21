"""
所有者后台 - 用户管理与权限调整
"""
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from datetime import datetime

from models import ArtistProfile, User, db


owner_bp = Blueprint('owner', __name__, url_prefix='/owner')

ROLE_OPTIONS = ['user', 'artist', 'admin', 'owner']


def owner_required(view_func):
    """限制只有 owner 角色可访问。"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'owner':
            abort(403)
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    """限制 admin 及 owner 访问。"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role not in {'admin', 'owner'}:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapper


@owner_bp.route('/users')
@login_required
@owner_required
def users():
    """用户管理页面"""
    all_users = User.query.filter_by(is_deleted=False).order_by(User.created_at.desc()).all()
    artists = ArtistProfile.query.filter_by(is_deleted=False).order_by(
        ArtistProfile.is_verified.asc(),
        ArtistProfile.created_at.desc(),
    ).all()
    return render_template('owner/users.html', users=all_users, role_options=ROLE_OPTIONS, artists=artists)


@owner_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@owner_required
def update_user_role(user_id):
    """调整用户权限角色"""
    user = User.query.filter_by(id=user_id, is_deleted=False).first_or_404()
    role = request.form.get('role', '').strip()

    if role not in ROLE_OPTIONS:
        flash('无效的用户角色', 'error')
        return redirect(url_for('owner.users'))

    if user.id == current_user.id and role != 'owner':
        flash('不能移除自己的所有者权限', 'error')
        return redirect(url_for('owner.users'))

    user.role = role
    db.session.commit()
    flash('用户权限已更新', 'success')
    return redirect(url_for('owner.users'))


@owner_bp.route('/users/<int:user_id>/status', methods=['POST'])
@login_required
@owner_required
def update_user_status(user_id):
    """启用或禁用用户"""
    user = User.query.filter_by(id=user_id, is_deleted=False).first_or_404()
    if user.id == current_user.id:
        flash('不能禁用自己的账号', 'error')
        return redirect(url_for('owner.users'))

    user.is_active = request.form.get('is_active') == 'true'
    db.session.commit()
    flash('用户状态已更新', 'success')
    return redirect(url_for('owner.users'))


@owner_bp.route('/artists/<int:artist_id>/verify', methods=['POST'])
@login_required
@admin_required
def verify_artist(artist_id):
    """认证或取消认证艺术家档案。管理员及所有者可操作。"""
    artist = ArtistProfile.query.filter_by(id=artist_id, is_deleted=False).first_or_404()
    artist.is_verified = request.form.get('is_verified') == 'true'
    artist.verified_by_id = current_user.id if artist.is_verified else None
    artist.verified_at = datetime.utcnow() if artist.is_verified else None
    db.session.commit()
    flash('艺术家认证状态已更新', 'success')
    return redirect(request.referrer or url_for('owner.users'))


@owner_bp.route('/artists/<int:artist_id>/review', methods=['POST'])
@login_required
@admin_required
def review_artist_update(artist_id):
    """审核艺术家档案修改。"""
    artist = ArtistProfile.query.filter_by(id=artist_id, is_deleted=False).first_or_404()
    action = request.form.get('action', '').strip()

    if action == 'approve':
        if artist.pending_name:
            artist.name = artist.pending_name
        artist.bio = artist.pending_bio
        artist.birth_year = artist.pending_birth_year
        artist.nationality = artist.pending_nationality
        artist.pending_name = None
        artist.pending_bio = None
        artist.pending_birth_year = None
        artist.pending_nationality = None
        artist.review_status = 'approved'
        artist.review_note = ''
        flash('艺术家资料修改已审核通过', 'success')
    elif action == 'reject':
        artist.review_status = 'rejected'
        artist.review_note = request.form.get('review_note', '').strip()
        flash('艺术家资料修改已驳回', 'info')
    else:
        flash('无效的审核操作', 'error')

    db.session.commit()
    return redirect(request.referrer or url_for('owner.users'))
