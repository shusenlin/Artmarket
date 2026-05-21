/**
 * ArtMarket - 前端主脚本
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('ArtMarket loaded');
    
    loadArtworks();
    
    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
});

/**
 * 加载艺术品列表
 */
async function loadArtworks() {
    const grid = document.getElementById('artworkGrid');
    if (!grid) return;
    
    try {
        const response = await fetch('/api/artworks');
        const data = await response.json();
        renderArtworks(data, grid);
    } catch (error) {
        console.error('加载艺术品失败:', error);
        grid.innerHTML = '<p class="text-light">加载失败，请稍后重试</p>';
    }
}

/**
 * 渲染艺术品卡片
 * @param {Array} artworks - 艺术品数据数组
 * @param {HTMLElement} container - 渲染容器
 */
function renderArtworks(artworks, container) {
    if (!artworks.length) {
        container.innerHTML = '<div class="empty-state"><h3>暂无藏品</h3><p>登录后登记第一件藏品。</p></div>';
        return;
    }

    container.innerHTML = artworks.map(artwork => `
        <article class="artwork-card">
            <a href="/artworks/${artwork.id}" class="artwork-image-link">
                ${artwork.thumbnail_url || artwork.image_url
                    ? `<img src="${artwork.thumbnail_url || artwork.image_url}" alt="${artwork.title}" class="artwork-image">`
                    : '<div class="artwork-image artwork-image-empty">暂无图片</div>'}
            </a>
            <div class="artwork-info">
                <h4><a href="/artworks/${artwork.id}">${artwork.title}</a></h4>
                ${artwork.artist_profile_id
                    ? `<p class="text-light">艺术家：<a class="inline-link" href="/artists/${artwork.artist_profile_id}">${artwork.artist_profile_name || '未命名艺术家'}</a>${artwork.artist_profile_verified ? '<span class="verified-badge">已认证</span>' : ''}</p>`
                    : ''}
                <p class="text-light">登记时间：${formatDate(artwork.registered_at || artwork.created_at)}</p>
            </div>
        </article>
    `).join('');
}

function formatDate(value) {
    if (!value) return '未知';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}
