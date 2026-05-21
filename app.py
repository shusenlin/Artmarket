"""
Flask 应用入口文件
艺术品展示与交易网站 - 核心应用初始化
"""
import os
from datetime import datetime
from sqlalchemy import inspect, text
from flask import Flask, render_template, jsonify, request
from werkzeug.exceptions import HTTPException
from flask_login import LoginManager

from config import config
from models import ArtistProfile, db, User


def create_app(config_name=None):
    """
    应用工厂函数 (Application Factory Pattern)
    支持多环境配置加载，便于测试和部署
    
    Args:
        config_name: 配置名称 ('development', 'production', 'testing')
                    默认为 None，使用 FLASK_ENV 环境变量或 default
    
    Returns:
        Flask 应用实例
    """
    # 确定配置名称
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    # 创建 Flask 应用实例
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )
    
    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 初始化扩展
    _init_extensions(app)
    
    # 注册路由
    _register_routes(app)
    
    # 注册蓝图
    _register_blueprints(app)

    # 开发阶段兼容已有 SQLite 数据库结构
    _ensure_development_schema(app)
    
    return app


def _init_extensions(app):
    """初始化 Flask 扩展"""
    # 初始化 SQLAlchemy
    db.init_app(app)
    
    # 初始化 Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        """根据用户 ID 加载用户"""
        return User.query.get(int(user_id))
    
    # 可选: 初始化 Flask-Migrate
    # from flask_migrate import Migrate
    # migrate = Migrate(app, db)
    
    # 可选: 开发环境启用 DebugToolbar
    # if app.config['DEBUG']:
    #     from flask_debugtoolbar import DebugToolbarExtension
    #     DebugToolbarExtension(app)


def _register_routes(app):
    """注册基础路由"""
    
    @app.route('/')
    def index():
        """首页路由"""
        return render_template('index.html')
    
    @app.route('/ping')
    def ping():
        """健康检查/测试路由"""
        return jsonify({
            'status': 'ok',
            'message': 'ArtMarket API is running',
            'environment': app.config.get('FLASK_ENV', 'unknown')
        })
    
    @app.errorhandler(404)
    def not_found(error):
        """404 错误处理"""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_too_large(error):
        """请求体过大错误处理"""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': '上传内容过大，请压缩图片或减少图片数量'}), 413
        return render_template('errors/500.html'), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 错误处理"""
        db.session.rollback()
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        """API 请求统一返回 JSON，页面请求仍使用 HTML 错误页。"""
        if isinstance(error, HTTPException):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': error.description or error.name}), error.code
            return error

        db.session.rollback()
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500


def _register_blueprints(app):
    """
    注册蓝图 (模块化路由)
    """
    from blueprints.auth import auth_bp
    from blueprints.artworks import artworks_bp
    from blueprints.profile import profile_bp
    from blueprints.owner import owner_bp
    from blueprints.assistant import assistant_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(artworks_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(assistant_bp)
    
    # 预留其他蓝图
    # from blueprints.artworks import artworks_bp
    # from blueprints.transactions import transactions_bp
    # app.register_blueprint(artworks_bp, url_prefix='/artworks')
    # app.register_blueprint(transactions_bp, url_prefix='/transactions')


def _ensure_development_schema(app):
    """开发环境下为已有 SQLite 表补齐新增字段。"""
    if not app.config.get('DEBUG'):
        return

    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if 'artworks' not in inspector.get_table_names():
            return

        existing_columns = {column['name'] for column in inspector.get_columns('artworks')}
        migrations = {
            'creation_process': "ALTER TABLE artworks ADD COLUMN creation_process TEXT",
            'collection_chronology': "ALTER TABLE artworks ADD COLUMN collection_chronology TEXT",
            'registered_at': "ALTER TABLE artworks ADD COLUMN registered_at DATETIME",
            'image_urls': "ALTER TABLE artworks ADD COLUMN image_urls TEXT",
            'video_url': "ALTER TABLE artworks ADD COLUMN video_url VARCHAR(500)",
            'reserve_price': "ALTER TABLE artworks ADD COLUMN reserve_price NUMERIC(12, 2)",
            'artist_profile_id': "ALTER TABLE artworks ADD COLUMN artist_profile_id INTEGER",
        }

        for column_name, ddl in migrations.items():
            if column_name not in existing_columns:
                db.session.execute(text(ddl))

        if 'artist_profiles' in inspector.get_table_names():
            existing_artist_columns = {column['name'] for column in inspector.get_columns('artist_profiles')}
            if 'artist_user_id' not in existing_artist_columns:
                db.session.execute(text("ALTER TABLE artist_profiles ADD COLUMN artist_user_id INTEGER"))
            artist_profile_migrations = {
                'review_status': "ALTER TABLE artist_profiles ADD COLUMN review_status VARCHAR(20) DEFAULT 'approved' NOT NULL",
                'pending_name': "ALTER TABLE artist_profiles ADD COLUMN pending_name VARCHAR(120)",
                'pending_bio': "ALTER TABLE artist_profiles ADD COLUMN pending_bio TEXT",
                'pending_birth_year': "ALTER TABLE artist_profiles ADD COLUMN pending_birth_year INTEGER",
                'pending_nationality': "ALTER TABLE artist_profiles ADD COLUMN pending_nationality VARCHAR(80)",
                'review_note': "ALTER TABLE artist_profiles ADD COLUMN review_note TEXT",
            }
            for column_name, ddl in artist_profile_migrations.items():
                if column_name not in existing_artist_columns:
                    db.session.execute(text(ddl))

        db.session.execute(text(
            "UPDATE artworks SET registered_at = created_at "
            "WHERE registered_at IS NULL"
        ))
        if not app.config.get('TESTING'):
            _ensure_owner_account()
            _ensure_artist_profiles()
        db.session.commit()


def _ensure_owner_account():
    """开发环境创建默认所有者账号，避免后台无入口。"""
    if User.query.filter_by(role='owner', is_deleted=False).first():
        return

    email = os.getenv('OWNER_EMAIL', 'owner@artmarket.local')
    password = os.getenv('OWNER_PASSWORD', 'Owner@123456')
    username = os.getenv('OWNER_USERNAME', 'owner')

    owner = User.query.filter_by(email=email).first()
    if owner is None:
        owner = User(username=username, email=email, role='owner', is_verified=True)
        owner.set_password(password)
        db.session.add(owner)
    else:
        owner.role = 'owner'
        owner.is_active = True
        owner.is_verified = True


def _ensure_artist_profiles():
    """为旧藏品补一个艺术家档案，避免历史数据没有艺术家分类。"""
    users = User.query.filter_by(is_deleted=False).all()
    for user in users:
        profile = ArtistProfile.query.filter_by(created_by_id=user.id, name=user.username, is_deleted=False).first()
        if profile is None:
            profile = ArtistProfile(
                name=user.username,
                bio=user.bio,
                is_verified=user.is_verified or user.role in {'artist', 'admin', 'owner'},
                artist_user_id=user.id,
                created_by_id=user.id,
                verified_by_id=user.id if user.is_verified or user.role in {'admin', 'owner'} else None,
                verified_at=datetime.utcnow() if user.is_verified or user.role in {'admin', 'owner'} else None,
            )
            db.session.add(profile)
            db.session.flush()
        for artwork in user.artworks.filter_by(is_deleted=False).all():
            if artwork.artist_profile_id is None:
                artwork.artist_profile_id = profile.id


# 命令行入口
if __name__ == '__main__':
    app = create_app()
    
    # 开发环境直接运行
    if app.config['DEBUG']:
        # 确保数据库目录存在 (SQLite)
        from config import Config
        db_uri = Config.SQLALCHEMY_DATABASE_URI
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            if db_path and not db_path.startswith(':memory:'):
                os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
        
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        # 生产环境建议使用 gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 app:app
        print("Production mode: use gunicorn to run this app")
