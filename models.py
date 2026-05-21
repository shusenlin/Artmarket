"""
数据库模型模块
包含 SQLAlchemy 实例初始化及基础模型定义
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

# 全局 SQLAlchemy 实例
# 注意：先声明实例，稍后在 app.py 中通过 init_app 绑定 Flask 应用
db = SQLAlchemy()


class TimestampMixin:
    """
    时间戳混合类
    为模型自动添加 created_at 和 updated_at 字段
    """
    from sqlalchemy import Column, DateTime
    from datetime import datetime
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """
    软删除混合类
    为模型添加 is_deleted 字段，支持逻辑删除
    """
    from sqlalchemy import Column, Boolean
    
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)


# =============================================================================
# 用户模型
# =============================================================================

class User(UserMixin, db.Model, TimestampMixin):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # 用户资料
    avatar = db.Column(db.String(255))  # 头像 URL (OSS)
    bio = db.Column(db.Text)  # 个人简介
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # 角色: 'user', 'artist', 'admin', 'owner'
    role = db.Column(db.String(20), default='user', nullable=False)
    
    # 软删除
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # 关系
    artworks = db.relationship('Artwork', backref='artist', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """序列化用户信息（不包含敏感数据）"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar': self.avatar,
            'bio': self.bio,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# 艺术家档案模型
# =============================================================================

class ArtistProfile(db.Model, TimestampMixin):
    """艺术家档案模型"""
    __tablename__ = 'artist_profiles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    bio = db.Column(db.Text)
    birth_year = db.Column(db.Integer)
    nationality = db.Column(db.String(80))
    is_verified = db.Column(db.Boolean, default=False, nullable=False, index=True)
    artist_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    review_status = db.Column(db.String(20), default='approved', nullable=False, index=True)
    pending_name = db.Column(db.String(120))
    pending_bio = db.Column(db.Text)
    pending_birth_year = db.Column(db.Integer)
    pending_nationality = db.Column(db.String(80))
    review_note = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)

    artist_user = db.relationship('User', foreign_keys=[artist_user_id], backref='artist_profile')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_artist_profiles')
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])

    def __repr__(self):
        return f'<ArtistProfile {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'bio': self.bio,
            'birth_year': self.birth_year,
            'nationality': self.nationality,
            'is_verified': self.is_verified,
            'artist_user_id': self.artist_user_id,
            'is_public_artist': not self.is_deleted,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'review_status': self.review_status,
        }


# =============================================================================
# 艺术品模型
# =============================================================================

class Artwork(db.Model, TimestampMixin):
    """艺术品模型"""
    __tablename__ = 'artworks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    creation_process = db.Column(db.Text)  # 创作心路历程
    collection_chronology = db.Column(db.Text)  # 收藏编年史
    price = db.Column(db.Numeric(12, 2))
    reserve_price = db.Column(db.Numeric(12, 2))  # 底价，仅后台/拥有者可见
    
    # 艺术家关联
    artist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    artist_profile_id = db.Column(db.Integer, db.ForeignKey('artist_profiles.id'))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 媒体资源
    image_url = db.Column(db.String(500))  # 原图 OSS URL
    thumbnail_url = db.Column(db.String(500))  # 缩略图 OSS URL
    image_urls = db.Column(db.Text)  # JSON 数组，保存多张图片路径
    video_url = db.Column(db.String(500))  # 本地上传视频路径
    media_type = db.Column(db.String(20), default='image')  # image/video
    
    # 分类标签
    category = db.Column(db.String(50))
    tags = db.Column(db.String(255))  # 逗号分隔的标签
    
    # 状态: 'draft', 'published', 'sold'
    status = db.Column(db.String(20), default='draft', nullable=False)
    
    # 软删除
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # 关系
    transactions = db.relationship('Transaction', backref='artwork', lazy='dynamic')
    comments = db.relationship('Comment', backref='artwork', lazy='dynamic')
    artist_profile = db.relationship('ArtistProfile', backref=db.backref('artworks', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Artwork {self.title}>'

    @property
    def images(self):
        """返回藏品全部图片路径，兼容旧的单图字段。"""
        if self.image_urls:
            try:
                urls = json.loads(self.image_urls)
                if isinstance(urls, list):
                    return [url for url in urls if url]
            except (TypeError, ValueError):
                pass
        return [self.image_url] if self.image_url else []
    
    def to_dict(self):
        """序列化艺术品信息"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'creation_process': self.creation_process,
            'collection_chronology': self.collection_chronology,
            'price': float(self.price) if self.price is not None else None,
            'reserve_price': float(self.reserve_price) if self.reserve_price is not None else None,
            'artist_id': self.artist_id,
            'artist_name': self.artist.username if self.artist else None,
            'artist_profile_id': self.artist_profile_id,
            'artist_profile_name': self.artist_profile.name if self.artist_profile else None,
            'artist_profile_verified': self.artist_profile.is_verified if self.artist_profile else False,
            'image_url': self.image_url,
            'image_urls': self.images,
            'video_url': self.video_url,
            'thumbnail_url': self.thumbnail_url,
            'media_type': self.media_type,
            'category': self.category,
            'tags': self.tags.split(',') if self.tags else [],
            'status': self.status,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# 藏品评论模型
# =============================================================================

class Comment(db.Model, TimestampMixin):
    """藏品评论与回复模型"""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    artwork_id = db.Column(db.Integer, db.ForeignKey('artworks.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), index=True)
    content = db.Column(db.Text, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)

    author = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))
    parent = db.relationship('Comment', remote_side=[id], backref=db.backref('replies', lazy='dynamic'))

    def __repr__(self):
        return f'<Comment {self.id}>'

    def to_dict(self):
        """序列化评论信息"""
        return {
            'id': self.id,
            'artwork_id': self.artwork_id,
            'user_id': self.user_id,
            'username': self.author.username if self.author else None,
            'user_avatar': self.author.avatar if self.author else None,
            'parent_id': self.parent_id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# 交易记录模型
# =============================================================================

class Transaction(db.Model, TimestampMixin):
    """交易记录模型"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联
    artwork_id = db.Column(db.Integer, db.ForeignKey('artworks.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 交易信息
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default='CNY', nullable=False)
    
    # 状态: 'pending', 'completed', 'cancelled', 'refunded'
    status = db.Column(db.String(20), default='pending', nullable=False)
    
    # 支付信息
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))  # 第三方支付流水号
    
    # 软删除
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # 关系
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='purchases')
    seller = db.relationship('User', foreign_keys=[seller_id], backref='sales')
    
    def __repr__(self):
        return f'<Transaction {self.id}>'
    
    def to_dict(self):
        """序列化交易信息"""
        return {
            'id': self.id,
            'artwork_id': self.artwork_id,
            'artwork_title': self.artwork.title if self.artwork else None,
            'buyer_id': self.buyer_id,
            'buyer_name': self.buyer.username if self.buyer else None,
            'seller_id': self.seller_id,
            'seller_name': self.seller.username if self.seller else None,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
