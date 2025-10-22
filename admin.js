// Admin Dashboard JavaScript

let currentUser = null;

// DOM Elements
const loginSection = document.getElementById('login-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');
const userEmailSpan = document.getElementById('user-email');
const articleForm = document.getElementById('article-form');
const formSuccess = document.getElementById('form-success');
const formError = document.getElementById('form-error');
const submitText = document.getElementById('submit-text');
const submitLoading = document.getElementById('submit-loading');
const recentArticlesDiv = document.getElementById('recent-articles');

// Check if user is already logged in
async function checkAuth() {
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session) {
        currentUser = session.user;
        showDashboard();
    } else {
        showLogin();
    }
}

// Show/Hide Sections
function showLogin() {
    loginSection.classList.remove('hidden');
    dashboardSection.classList.add('hidden');
}

function showDashboard() {
    loginSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    userEmailSpan.textContent = currentUser.email;
    loadRecentArticles();
}

// Login Handler
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    loginError.classList.add('hidden');
    
    try {
        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password
        });
        
        if (error) throw error;
        
        currentUser = data.user;
        showDashboard();
        
    } catch (error) {
        console.error('Login error:', error);
        loginError.textContent = error.message || 'Failed to login. Please check your credentials.';
        loginError.classList.remove('hidden');
    }
});

// Logout Handler
logoutBtn.addEventListener('click', async () => {
    try {
        await supabase.auth.signOut();
        currentUser = null;
        showLogin();
        loginForm.reset();
    } catch (error) {
        console.error('Logout error:', error);
    }
});

// Article Form Handler
articleForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Clear previous messages
    formSuccess.classList.add('hidden');
    formError.classList.add('hidden');
    
    // Show loading state
    submitText.classList.add('hidden');
    submitLoading.classList.remove('hidden');
    
    // Get form data
    const formData = {
        title: document.getElementById('article-title').value.trim(),
        author: document.getElementById('article-author').value.trim() || 'Anonymous',
        excerpt: document.getElementById('article-excerpt').value.trim(),
        content: document.getElementById('article-content').value.trim(),
        image_url: document.getElementById('article-image').value.trim() || null
    };
    
    try {
        const { data, error } = await supabase
            .from('articles')
            .insert([formData])
            .select();
        
        if (error) throw error;
        
        // Show success message
        formSuccess.textContent = '✓ Article published successfully!';
        formSuccess.classList.remove('hidden');
        
        // Reset form
        articleForm.reset();
        
        // Reload recent articles
        loadRecentArticles();
        
        // Hide success message after 5 seconds
        setTimeout(() => {
            formSuccess.classList.add('hidden');
        }, 5000);
        
    } catch (error) {
        console.error('Error creating article:', error);
        formError.textContent = 'Failed to publish article: ' + error.message;
        formError.classList.remove('hidden');
    } finally {
        // Reset button state
        submitText.classList.remove('hidden');
        submitLoading.classList.add('hidden');
    }
});

// Load Recent Articles
async function loadRecentArticles() {
    try {
        const { data: articles, error } = await supabase
            .from('articles')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(10);
        
        if (error) throw error;
        
        if (!articles || articles.length === 0) {
            recentArticlesDiv.innerHTML = '<p class="loading-small">No articles yet. Create your first one!</p>';
            return;
        }
        
        renderRecentArticles(articles);
        
    } catch (error) {
        console.error('Error loading articles:', error);
        recentArticlesDiv.innerHTML = '<p class="loading-small">Failed to load articles.</p>';
    }
}

// Render Recent Articles
function renderRecentArticles(articles) {
    recentArticlesDiv.innerHTML = '';
    
    articles.forEach(article => {
        const articleEl = document.createElement('div');
        articleEl.className = 'article-item';
        
        const date = new Date(article.created_at);
        const formattedDate = date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        articleEl.innerHTML = `
            <div class="article-item-title">${escapeHtml(article.title)}</div>
            <div class="article-item-meta">
                <span>By ${escapeHtml(article.author || 'Anonymous')}</span>
                <span>${formattedDate}</span>
            </div>
            <div class="article-item-actions">
                <button class="btn btn-small btn-danger" onclick="deleteArticle('${article.id}')">Delete</button>
            </div>
        `;
        
        recentArticlesDiv.appendChild(articleEl);
    });
}

// Delete Article
async function deleteArticle(articleId) {
    if (!confirm('Are you sure you want to delete this article?')) {
        return;
    }
    
    try {
        const { error } = await supabase
            .from('articles')
            .delete()
            .eq('id', articleId);
        
        if (error) throw error;
        
        // Reload articles
        loadRecentArticles();
        
    } catch (error) {
        console.error('Error deleting article:', error);
        alert('Failed to delete article: ' + error.message);
    }
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});

// Listen for auth state changes
supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_IN') {
        currentUser = session.user;
        showDashboard();
    } else if (event === 'SIGNED_OUT') {
        currentUser = null;
        showLogin();
    }
});
