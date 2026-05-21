"""
个人信息蓝图 - 个人资料与已登记藏品
"""
from sqlalchemy import or_
from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash
from flask_login import current_user, login_required

from models import ArtistProfile, Artwork, User, db
from blueprints.artworks import _save_uploaded_image


profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """个人信息界面"""
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        username = data.get('username', '').strip()
        if not username or len(username) < 2:
            if request.is_json:
                return jsonify({'error': '用户名至少 2 个字符'}), 400
            flash('用户名至少 2 个字符', 'error')
            return redirect(url_for('profile.profile'))

        existing_user = User.query.filter(User.username == username, User.id != current_user.id).first()
        if existing_user:
            if request.is_json:
                return jsonify({'error': '用户名已被使用'}), 400
            flash('用户名已被使用', 'error')
            return redirect(url_for('profile.profile'))

        current_user.username = username
        current_user.bio = data.get('bio', '').strip()
        try:
            avatar_url = _save_uploaded_image(request.files.get('avatar_image'), 'avatars')
        except ValueError as exc:
            if request.is_json:
                return jsonify({'error': str(exc)}), 400
            flash(str(exc), 'error')
            return redirect(url_for('profile.profile'))

        if avatar_url:
            current_user.avatar = avatar_url

        db.session.commit()

        if request.is_json:
            return jsonify({'message': '个人信息已更新', 'user': current_user.to_dict()})
        flash('个人信息已更新', 'success')
        return redirect(url_for('profile.profile'))

    artworks = (
        Artwork.query
        .filter_by(artist_id=current_user.id, is_deleted=False)
        .order_by(Artwork.registered_at.desc(), Artwork.created_at.desc())
        .all()
    )
    artist_profiles = (
        ArtistProfile.query
        .filter(
            ArtistProfile.is_deleted == False,
            or_(
                ArtistProfile.created_by_id == current_user.id,
                ArtistProfile.artist_user_id == current_user.id,
            ),
        )
        .order_by(ArtistProfile.created_at.desc())
        .all()
    )
    return render_template('profile/index.html', artworks=artworks, artist_profiles=artist_profiles)


@profile_bp.route('/profile/artists/<int:artist_id>', methods=['POST'])
@login_required
def update_artist_profile(artist_id):
    """提交自己创建或关联的艺术家档案修改，等待管理员审核。"""
    artist = (
        ArtistProfile.query
        .filter(
            ArtistProfile.id == artist_id,
            ArtistProfile.is_deleted == False,
            or_(
                ArtistProfile.created_by_id == current_user.id,
                ArtistProfile.artist_user_id == current_user.id,
            ),
        )
        .first_or_404()
    )

    data = request.get_json(silent=True) or request.form
    name = data.get('name', '').strip()
    if not name:
        if request.is_json:
            return jsonify({'error': '艺术家名称不能为空'}), 400
        flash('艺术家名称不能为空', 'error')
        return redirect(url_for('profile.profile'))

    birth_year = None
    raw_birth_year = data.get('birth_year', '').strip()
    if raw_birth_year:
        try:
            birth_year = int(raw_birth_year)
        except ValueError:
            if request.is_json:
                return jsonify({'error': '出生年份格式不正确'}), 400
            flash('出生年份格式不正确', 'error')
            return redirect(url_for('profile.profile'))

    artist.pending_name = name
    artist.pending_bio = data.get('bio', '').strip()
    artist.pending_birth_year = birth_year
    artist.pending_nationality = data.get('nationality', '').strip()
    artist.review_status = 'pending'
    artist.review_note = ''
    db.session.commit()

    if request.is_json:
        return jsonify({'message': '艺术家资料修改已提交审核', 'artist': artist.to_dict()})
    flash('艺术家资料修改已提交审核', 'success')
    return redirect(url_for('profile.profile'))
