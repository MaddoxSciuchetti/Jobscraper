// Tab Switching Functionality
function switchTab(tabName) {
    // Remove active class from all tabs and content
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Add active class to selected tab and content
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');

    // Load articles when switching to articles tab
    if (tabName === 'articles') {
        loadArticles();
    }
}

// Event listeners for tab buttons
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.getAttribute('data-tab');
        switchTab(tabName);
    });
});

// Articles Management
let articlesLoaded = false;

async function loadArticles() {
    // Only load once
    if (articlesLoaded) return;

    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error');
    const articlesGridEl = document.getElementById('articles-grid');
    const noArticlesEl = document.getElementById('no-articles');

    // Show loading state
    loadingEl.classList.remove('hidden');
    errorEl.classList.add('hidden');
    noArticlesEl.classList.add('hidden');
    articlesGridEl.innerHTML = '';

    try {
        // Fetch articles from Supabase
        const { data: articles, error } = await supabase
            .from('articles')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) {
            throw error;
        }

        // Hide loading
        loadingEl.classList.add('hidden');

        // Check if articles exist
        if (!articles || articles.length === 0) {
            noArticlesEl.classList.remove('hidden');
            articlesLoaded = true;
            return;
        }

        // Render articles
        renderArticles(articles);
        articlesLoaded = true;

    } catch (error) {
        console.error('Error loading articles:', error);
        loadingEl.classList.add('hidden');
        errorEl.classList.remove('hidden');
    }
}

function renderArticles(articles) {
    const articlesGridEl = document.getElementById('articles-grid');
    
    articles.forEach(article => {
        const articleCard = createArticleCard(article);
        articlesGridEl.appendChild(articleCard);
    });
}

function createArticleCard(article) {
    const card = document.createElement('div');
    card.className = 'article-card';
    
    // Format date
    const date = new Date(article.created_at);
    const formattedDate = date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });

    // Truncate excerpt if too long
    const excerpt = article.excerpt 
        ? (article.excerpt.length > 150 
            ? article.excerpt.substring(0, 150) + '...' 
            : article.excerpt)
        : 'No description available.';

    card.innerHTML = `
        ${article.image_url 
            ? `<img src="${article.image_url}" alt="${article.title}" class="article-image">` 
            : '<div class="article-image"></div>'}
        <div class="article-content">
            <h3 class="article-title">${escapeHtml(article.title)}</h3>
            <p class="article-excerpt">${escapeHtml(excerpt)}</p>
            <div class="article-meta">
                <span class="article-author">${escapeHtml(article.author || 'Anonymous')}</span>
                <span class="article-date">${formattedDate}</span>
            </div>
        </div>
    `;

    // Add click handler if article has a URL
    if (article.url) {
        card.addEventListener('click', () => {
            window.open(article.url, '_blank');
        });
    }

    return card;
}

// Utility function to escape HTML and prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('App initialized');
    
    // Check Supabase connection
    if (!SUPABASE_CONFIG.anonKey || SUPABASE_CONFIG.anonKey === 'YOUR_SUPABASE_ANON_KEY_HERE') {
        console.warn('⚠️ Supabase anon key not configured. Please update config.js');
    }
});
