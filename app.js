// Tab Switching Functionality
function switchTab(tabName) {
    // Remove active class from all tabs and content
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Add active class to selected tab and content
    const activeLink = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
    document.getElementById(tabName).classList.add('active');

    // Load articles when switching to articles tab
    if (tabName === 'articles') {
        loadArticles();
    }
}

// Event listeners for nav links
document.querySelectorAll('.nav-link[data-tab]').forEach(link => {
    link.addEventListener('click', () => {
        const tabName = link.getAttribute('data-tab');
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
    const articlesListEl = document.getElementById('articles-list');
    const noArticlesEl = document.getElementById('no-articles');

    // Show loading state
    loadingEl.classList.remove('hidden');
    errorEl.classList.add('hidden');
    noArticlesEl.classList.add('hidden');
    articlesListEl.innerHTML = '';

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
    const articlesListEl = document.getElementById('articles-list');
    
    articles.forEach(article => {
        const articleItem = createArticleItem(article);
        articlesListEl.appendChild(articleItem);
    });
}

function createArticleItem(article) {
    const item = document.createElement('div');
    item.className = 'article-item';
    
    // Format date
    const date = new Date(article.created_at);
    const formattedDate = date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });

    // Use excerpt or content
    const excerpt = article.excerpt || article.content || '';

    item.innerHTML = `
        <h3 class="article-title">${escapeHtml(article.title)}</h3>
        ${excerpt ? `<p class="article-excerpt">${escapeHtml(excerpt)}</p>` : ''}
        <div class="article-meta">
            <span class="article-author">${escapeHtml(article.author || 'Anonymous')}</span>
            <span class="article-date">${formattedDate}</span>
        </div>
    `;

    return item;
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
