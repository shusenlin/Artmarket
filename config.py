"""
应用配置模块
基于 python-dotenv 读取环境变量，支持多环境配置
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env 文件中的环境变量
load_dotenv(os.path.join(BASE_DIR, '.env'))


def _sqlite_url_from_path(path):
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return f"sqlite:///{os.path.abspath(path)}"


def _database_uri():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        sqlite_prefix = 'sqlite:///'
        if database_url.startswith(sqlite_prefix) and not database_url.startswith('sqlite:////'):
            raw_path = database_url[len(sqlite_prefix):]
            if raw_path != ':memory:':
                return _sqlite_url_from_path(raw_path)
        return database_url

    database_path = os.getenv('DATABASE_PATH', os.path.join(BASE_DIR, 'instance', 'artmarket.db'))
    return _sqlite_url_from_path(database_path)


class Config:
    """基础配置类"""
    
    # Flask 核心配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    
    # 数据库配置
    # 构建数据库路径（使用绝对路径避免相对路径问题）
    _base_dir = BASE_DIR
    _db_path = os.getenv('DATABASE_PATH', os.path.join(_base_dir, 'instance', 'artmarket.db'))
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    
    # 阿里云 OSS 配置
    OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID')
    OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET')
    OSS_BUCKET_NAME = os.getenv('OSS_BUCKET_NAME')
    OSS_ENDPOINT = os.getenv('OSS_ENDPOINT')
    OSS_BASE_URL = os.getenv('OSS_BASE_URL', '')
    
    # OSS 路径配置
    OSS_ARTWORKS_FOLDER = os.getenv('OSS_ARTWORKS_FOLDER', 'artworks/')
    OSS_THUMBNAILS_FOLDER = os.getenv('OSS_THUMBNAILS_FOLDER', 'thumbnails/')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))  # 默认 50MB
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,webp,mp4,webm').split(','))
    
    # 分页配置
    ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', 20))
    
    # 时区
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Singapore')
    
    @staticmethod
    def init_app(app):
        """应用初始化钩子，子类可重写"""
        pass
    
    @classmethod
    def is_oss_configured(cls):
        """检查 OSS 配置是否完整"""
        return all([
            cls.OSS_ACCESS_KEY_ID,
            cls.OSS_ACCESS_KEY_SECRET,
            cls.OSS_BUCKET_NAME,
            cls.OSS_ENDPOINT
        ])


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
    @staticmethod
    def init_app(app):
        # 开发环境可添加额外配置
        pass


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境建议启用更严格的安全配置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    @staticmethod
    def init_app(app):
        # 生产环境日志配置等
        pass


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    # 测试使用独立数据库
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # 测试时禁用 CSRF


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
