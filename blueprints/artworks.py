"""
藏品蓝图 - 藏品登记、列表、详情与 API
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from mimetypes import guess_extension
import json
import os
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for, flash
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models import ArtistProfile, Artwork, Comment, db


artworks_bp = Blueprint('artworks', __name__)

ARTWORK_CATEGORIES = [
    '绘画',
    '书法',
    '雕塑',
    '陶瓷',
    '影像',
    '摄影',
    '装置',
    '数字艺术',
    '其他',
]

HOME_CATEGORIES = ['绘画', '书法', '雕塑', '陶瓷']

PRIVILEGED_ROLES = {'admin', 'owner'}

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov'}
IMAGE_MIME_EXTENSIONS = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp',
}
VIDEO_MIME_EXTENSIONS = {
    'video/mp4': 'mp4',
    'video/webm': 'webm',
    'video/ogg': 'ogg',
    'video/quicktime': 'mov',
}


def _extension_from_upload(file_storage, allowed_extensions, mime_extensions):
    """从原始文件名或 MIME 类型解析扩展名。"""
    original_name = file_storage.filename or ''
    if '.' in original_name:
        extension = original_name.rsplit('.', 1)[-1].lower()
        if extension == 'jpeg':
            return 'jpg'
        if extension in allowed_extensions:
            return extension

    mime_extension = mime_extensions.get(file_storage.mimetype)
    if mime_extension:
        return mime_extension

    guessed = guess_extension(file_storage.mimetype or '')
    if guessed:
        guessed_extension = guessed.lstrip('.').lower()
        if guessed_extension == 'jpe':
            guessed_extension = 'jpg'
        if guessed_extension in allowed_extensions:
            return guessed_extension

    return ''


def _save_uploaded_file(file_storage, folder, allowed_extensions, mime_extensions, error_message):
    """保存上传文件到 static/uploads 下，并返回可访问路径。"""
    if not file_storage or not file_storage.filename:
        return ''

    extension = _extension_from_upload(file_storage, allowed_extensions, mime_extensions)
    if extension not in allowed_extensions:
        raise ValueError(error_message)

    upload_root = os.path.join(current_app.static_folder, 'uploads', folder)
    os.makedirs(upload_root, exist_ok=True)
    saved_name = f'{datetime.utcnow().strftime("%Y%m%d%H%M%S")}-{uuid4().hex}.{extension}'
    file_storage.save(os.path.join(upload_root, saved_name))
    return url_for('static', filename=f'uploads/{folder}/{saved_name}')


def _save_uploaded_image(file_storage, folder):
    """保存上传图片到 static/uploads 下，并返回可访问路径。"""
    return _save_uploaded_file(
        file_storage,
        folder,
        IMAGE_EXTENSIONS,
        IMAGE_MIME_EXTENSIONS,
        '仅支持 png、jpg、jpeg、gif、webp 图片',
    )


def _save_uploaded_video(file_storage, folder):
    """保存上传视频到 static/uploads 下，并返回可访问路径。"""
    return _save_uploaded_file(
        file_storage,
        folder,
        VIDEO_EXTENSIONS,
        VIDEO_MIME_EXTENSIONS,
        '仅支持 mp4、webm、ogg、mov 视频',
    )


def _save_uploaded_images(file_storages, folder):
    """保存多张上传图片，返回路径列表。"""
    urls = []
    for file_storage in file_storages:
        url = _save_uploaded_image(file_storage, folder)
        if url:
            urls.append(url)
    return urls


def _parse_money(value, field_name):
    """解析金额字段，空值返回 None。"""
    value = (value or '').strip()
    if not value:
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f'{field_name}格式不正确') from exc
    if amount < 0:
        raise ValueError(f'{field_name}不能为负数')
    return amount.quantize(Decimal('0.01'))


@artworks_bp.route('/artworks')
def list_artworks():
    """藏品列表"""
    category = request.args.get('category', '').strip()
    artist_profile_id = request.args.get('artist_profile_id', '').strip()

    query = Artwork.query.filter_by(is_deleted=False)
    if category in ARTWORK_CATEGORIES:
        query = query.filter(Artwork.category == category)
    if artist_profile_id:
        try:
            query = query.filter(Artwork.artist_profile_id == int(artist_profile_id))
        except ValueError:
            artist_profile_id = ''

    artworks = query.order_by(Artwork.registered_at.desc(), Artwork.created_at.desc()).all()
    artist_profiles = (
        ArtistProfile.query
        .filter_by(is_deleted=False)
        .order_by(ArtistProfile.is_verified.desc(), ArtistProfile.name.asc())
        .all()
    )
    return render_template(
        'artworks/list.html',
        artworks=artworks,
        categories=ARTWORK_CATEGORIES,
        artist_profiles=artist_profiles,
        selected_category=category if category in ARTWORK_CATEGORIES else '',
        selected_artist_profile_id=artist_profile_id,
    )


@artworks_bp.route('/artists')
def list_artists():
    """艺术家列表"""
    artists = (
        ArtistProfile.query
        .filter_by(is_deleted=False)
        .order_by(ArtistProfile.is_verified.desc(), ArtistProfile.name.asc())
        .all()
    )
    return render_template('artists/list.html', artists=artists)


@artworks_bp.route('/artists/<int:artist_id>')
def detail_artist(artist_id):
    """艺术家档案页"""
    artist = ArtistProfile.query.filter_by(id=artist_id, is_deleted=False).first_or_404()
    artworks = (
        Artwork.query
        .filter_by(artist_profile_id=artist.id, is_deleted=False)
        .order_by(Artwork.registered_at.desc(), Artwork.created_at.desc())
        .all()
    )
    return render_template('artists/detail.html', artist=artist, artworks=artworks)


@artworks_bp.route('/artworks/new', methods=['GET', 'POST'])
@login_required
def create_artwork():
    """登记藏品"""
    artist_profiles = (
        ArtistProfile.query
        .filter_by(is_deleted=False)
        .order_by(ArtistProfile.is_verified.desc(), ArtistProfile.name.asc())
        .all()
    )
    if request.method == 'GET':
        return render_template('artworks/new.html', categories=ARTWORK_CATEGORIES, artist_profiles=artist_profiles)

    data = request.get_json(silent=True) or request.form
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    creation_process = data.get('creation_process', '').strip()
    collection_chronology = data.get('collection_chronology', '').strip()
    category = data.get('category', '').strip()
    tags = data.get('tags', '').strip()
    artist_mode = data.get('artist_mode', 'existing').strip()
    artist_profile_id = data.get('artist_profile_id', '').strip()
    new_artist_name = data.get('new_artist_name', '').strip()
    new_artist_bio = data.get('new_artist_bio', '').strip()
    new_artist_birth_year = data.get('new_artist_birth_year', '').strip()
    new_artist_nationality = data.get('new_artist_nationality', '').strip()
    new_artist_is_self = data.get('new_artist_is_self') == 'true'

    if not title:
        if request.is_json:
            return jsonify({'error': '藏品名称不能为空'}), 400
        flash('藏品名称不能为空', 'error')
        return redirect(url_for('artworks.create_artwork'))

    if category not in ARTWORK_CATEGORIES:
        if request.is_json:
            return jsonify({'error': '请选择有效的藏品分类'}), 400
        flash('请选择有效的藏品分类', 'error')
        return redirect(url_for('artworks.create_artwork'))

    artist_profile = None
    if artist_mode == 'new':
        if not new_artist_name:
            if request.is_json:
                return jsonify({'error': '新增艺术家名称不能为空'}), 400
            flash('新增艺术家名称不能为空', 'error')
            return redirect(url_for('artworks.create_artwork'))

        birth_year = None
        if new_artist_birth_year:
            try:
                birth_year = int(new_artist_birth_year)
            except ValueError:
                if request.is_json:
                    return jsonify({'error': '艺术家出生年份格式不正确'}), 400
                flash('艺术家出生年份格式不正确', 'error')
                return redirect(url_for('artworks.create_artwork'))

        artist_profile = ArtistProfile(
            name=new_artist_name,
            bio=new_artist_bio,
            birth_year=birth_year,
            nationality=new_artist_nationality,
            artist_user_id=current_user.id if new_artist_is_self else None,
            created_by_id=current_user.id,
        )
        db.session.add(artist_profile)
        db.session.flush()
    else:
        try:
            selected_artist_id = int(artist_profile_id)
        except (TypeError, ValueError):
            selected_artist_id = 0
        artist_profile = (
            ArtistProfile.query
            .filter(
                ArtistProfile.id == selected_artist_id,
                ArtistProfile.is_deleted == False,
            )
            .first()
        )
        if not artist_profile:
            if request.is_json:
                return jsonify({'error': '请选择已有艺术家，或新增艺术家档案'}), 400
            flash('请选择已有艺术家，或新增艺术家档案', 'error')
            return redirect(url_for('artworks.create_artwork'))

    try:
        price = _parse_money(data.get('price'), '标价')
        reserve_price = _parse_money(data.get('reserve_price'), '底价')
    except ValueError as exc:
        if request.is_json:
            return jsonify({'error': str(exc)}), 400
        flash(str(exc), 'error')
        return redirect(url_for('artworks.create_artwork'))

    try:
        image_urls = _save_uploaded_images(request.files.getlist('artwork_images'), 'artworks')
        video_url = _save_uploaded_video(request.files.get('artwork_video'), 'videos')
    except ValueError as exc:
        if request.is_json:
            return jsonify({'error': str(exc)}), 400
        flash(str(exc), 'error')
        return redirect(url_for('artworks.create_artwork'))

    if not image_urls:
        if request.is_json:
            return jsonify({'error': '请至少上传一张藏品图片'}), 400
        flash('请至少上传一张藏品图片', 'error')
        return redirect(url_for('artworks.create_artwork'))

    cover_image = image_urls[0] if image_urls else ''

    artwork = Artwork(
        title=title,
        description=description,
        price=price,
        reserve_price=reserve_price,
        image_url=cover_image,
        thumbnail_url=cover_image,
        image_urls=json.dumps(image_urls, ensure_ascii=False),
        video_url=video_url,
        media_type='video' if video_url else 'image',
        creation_process=creation_process,
        collection_chronology=collection_chronology,
        category=category,
        tags=tags,
        artist_id=current_user.id,
        artist_profile_id=artist_profile.id,
        registered_at=datetime.utcnow(),
        status='published',
    )
    db.session.add(artwork)
    db.session.commit()

    if request.is_json:
        return jsonify({'message': '登记成功', 'artwork': artwork.to_dict()}), 201
    flash('藏品登记成功', 'success')
    return redirect(url_for('artworks.detail_artwork', artwork_id=artwork.id))


@artworks_bp.route('/artworks/<int:artwork_id>')
def detail_artwork(artwork_id):
    """藏品详情"""
    artwork = Artwork.query.filter_by(id=artwork_id, is_deleted=False).first_or_404()
    all_comments = (
        Comment.query
        .filter_by(artwork_id=artwork.id, is_deleted=False)
        .order_by(Comment.created_at.asc())
        .all()
    )
    top_comments = [comment for comment in all_comments if comment.parent_id is None]
    children_by_parent = {}
    for comment in all_comments:
        if comment.parent_id is not None:
            children_by_parent.setdefault(comment.parent_id, []).append(comment)

    def flatten_replies(parent_id):
        replies = []
        for child in children_by_parent.get(parent_id, []):
            replies.append(child)
            replies.extend(flatten_replies(child.id))
        return replies

    replies_by_root = {
        comment.id: flatten_replies(comment.id)
        for comment in top_comments
    }

    return render_template(
        'artworks/detail.html',
        artwork=artwork,
        comments=top_comments,
        replies_by_root=replies_by_root,
        comment_count=len(all_comments),
    )


@artworks_bp.route('/artworks/<int:artwork_id>/delete', methods=['POST'])
@login_required
def delete_artwork(artwork_id):
    """删除藏品。仅藏品登记人可操作。"""
    artwork = Artwork.query.filter_by(id=artwork_id, is_deleted=False).first_or_404()

    if artwork.artist_id != current_user.id:
        if request.is_json:
            return jsonify({'error': '只有藏品拥有者可以删除'}), 403
        flash('只有藏品拥有者可以删除', 'error')
        return redirect(url_for('artworks.detail_artwork', artwork_id=artwork.id))

    artwork.is_deleted = True
    Comment.query.filter_by(artwork_id=artwork.id, is_deleted=False).update(
        {'is_deleted': True},
        synchronize_session=False,
    )
    db.session.commit()

    if request.is_json:
        return jsonify({'message': '藏品已删除'})
    flash('藏品已删除', 'success')
    return redirect(url_for('profile.profile'))


@artworks_bp.route('/artworks/<int:artwork_id>/prices', methods=['POST'])
@login_required
def update_artwork_prices(artwork_id):
    """更新藏品标价和底价。仅藏品登记人可操作。"""
    artwork = Artwork.query.filter_by(id=artwork_id, is_deleted=False).first_or_404()

    if artwork.artist_id != current_user.id:
        if request.is_json:
            return jsonify({'error': '只有藏品拥有者可以调整价格'}), 403
        flash('只有藏品拥有者可以调整价格', 'error')
        return redirect(url_for('profile.profile'))

    data = request.get_json(silent=True) or request.form
    try:
        artwork.price = _parse_money(data.get('price'), '标价')
        artwork.reserve_price = _parse_money(data.get('reserve_price'), '底价')
    except ValueError as exc:
        if request.is_json:
            return jsonify({'error': str(exc)}), 400
        flash(str(exc), 'error')
        return redirect(url_for('profile.profile'))

    db.session.commit()

    if request.is_json or request.accept_mimetypes.best == 'application/json':
        return jsonify({'message': '价格已更新', 'artwork': artwork.to_dict()})
    flash('价格已更新', 'success')
    return redirect(url_for('profile.profile'))


@artworks_bp.route('/artworks/<int:artwork_id>/comments', methods=['POST'])
@login_required
def create_comment(artwork_id):
    """创建藏品评论或回复"""
    artwork = Artwork.query.filter_by(id=artwork_id, is_deleted=False).first_or_404()
    data = request.get_json(silent=True) or request.form
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')

    if not content:
        if request.is_json:
            return jsonify({'error': '评论内容不能为空'}), 400
        flash('评论内容不能为空', 'error')
        return redirect(url_for('artworks.detail_artwork', artwork_id=artwork.id) + '#comments')

    parent_comment = None
    if parent_id:
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            parent_id = 0

        parent_comment = Comment.query.filter_by(
            id=parent_id,
            artwork_id=artwork.id,
            is_deleted=False,
        ).first()
        if not parent_comment:
            if request.is_json:
                return jsonify({'error': '回复的评论不存在'}), 404
            flash('回复的评论不存在', 'error')
            return redirect(url_for('artworks.detail_artwork', artwork_id=artwork.id) + '#comments')

    comment = Comment(
        artwork_id=artwork.id,
        user_id=current_user.id,
        parent_id=parent_comment.id if parent_comment else None,
        content=content,
    )
    db.session.add(comment)
    db.session.commit()

    if request.is_json:
        return jsonify({'message': '评论成功', 'comment': comment.to_dict()}), 201
    return redirect(url_for('artworks.detail_artwork', artwork_id=artwork.id) + '#comments')


@artworks_bp.route('/artworks/<int:artwork_id>/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(artwork_id, comment_id):
    """删除评论。仅评论作者或管理员可删除。"""
    artwork = Artwork.query.filter_by(id=artwork_id, is_deleted=False).first_or_404()
    comment = Comment.query.filter_by(
        id=comment_id,
        artwork_id=artwork.id,
        is_deleted=False,
    ).first_or_404()

    if current_user.role != 'admin' and comment.user_id != current_user.id:
        if request.is_json:
            return jsonify({'error': '没有权限删除这条评论'}), 403
        flash('没有权限删除这条评论', 'error')
        return redirect(url_for('artworks.detail_artwork', artwork_id=artwork.id) + '#comments')

    all_comments = Comment.query.filter_by(artwork_id=artwork.id, is_deleted=False).all()
    children_by_parent = {}
    for item in all_comments:
        if item.parent_id is not None:
            children_by_parent.setdefault(item.parent_id, []).append(item)

    def mark_deleted(item):
        item.is_deleted = True
        for child in children_by_parent.get(item.id, []):
            mark_deleted(child)

    mark_deleted(comment)
    db.session.commit()

    if request.is_json:
        return jsonify({'message': '评论已删除'})
    flash('评论已删除', 'success')
    return redirect(url_for('artworks.detail_artwork', artwork_id=artwork.id) + '#comments')


@artworks_bp.route('/api/artworks')
def api_artworks():
    """藏品列表 API"""
    artworks = (
        Artwork.query
        .filter_by(is_deleted=False)
        .order_by(Artwork.registered_at.desc(), Artwork.created_at.desc())
        .limit(24)
        .all()
    )
    return jsonify([artwork.to_dict() for artwork in artworks])
