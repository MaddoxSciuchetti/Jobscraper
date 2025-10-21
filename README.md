# Handwerk - Simple Article Webpage

A clean and modern webpage with two tabs (Home and Articles) connected to Supabase for dynamic content management.

## Features

- 🎨 Modern, responsive UI design
- 📱 Mobile-friendly layout
- 🔄 Dynamic article loading from Supabase
- ⚡ Fast and lightweight
- 🎯 Simple tab navigation
- 🔒 Secure database connection with Row Level Security

## Tech Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: Supabase (PostgreSQL)
- **CDN**: Supabase JS Client

## Setup Instructions

### 1. Database Setup

1. Go to your [Supabase Dashboard](https://app.supabase.com)
2. Navigate to the SQL Editor
3. Copy and paste the contents of `setup.sql`
4. Run the SQL script to create the `articles` table and sample data

### 2. Get Your Supabase Credentials

1. In your Supabase project, go to **Settings** → **API**
2. Copy your **Project URL** (already configured: `https://hiapewazeymhzwkenlyg.supabase.co`)
3. Copy your **anon/public key**

### 3. Configure the Application

1. Open `config.js`
2. Replace `YOUR_SUPABASE_ANON_KEY_HERE` with your actual Supabase anon key:

```javascript
const SUPABASE_CONFIG = {
    url: 'https://hiapewazeymhzwkenlyg.supabase.co',
    anonKey: 'your-actual-anon-key-here'
};
```

### 4. Run the Application

Simply open `index.html` in your web browser, or use a local server:

**Option 1: Direct File**
```bash
open index.html
```

**Option 2: Python Server**
```bash
python3 -m http.server 8000
# Then visit http://localhost:8000
```

**Option 3: Node.js Server**
```bash
npx serve
```

## Project Structure

```
webpage.handwerk/
├── index.html          # Main HTML structure
├── styles.css          # All styling and responsive design
├── app.js             # Application logic and Supabase integration
├── config.js          # Supabase configuration
├── setup.sql          # Database schema and sample data
├── .env               # Database credentials (not used in frontend)
└── README.md          # This file
```

## Database Schema

### Articles Table

| Column      | Type      | Description                          |
|-------------|-----------|--------------------------------------|
| id          | UUID      | Primary key (auto-generated)         |
| title       | TEXT      | Article title                        |
| excerpt     | TEXT      | Short description/preview            |
| content     | TEXT      | Full article content (optional)      |
| author      | TEXT      | Author name                          |
| image_url   | TEXT      | URL to article image                 |
| url         | TEXT      | External link to full article        |
| created_at  | TIMESTAMP | Creation timestamp                   |
| updated_at  | TIMESTAMP | Last update timestamp                |

## Usage

### Adding New Articles

You can add articles through:

1. **Supabase Dashboard**:
   - Go to Table Editor → articles
   - Click "Insert row"
   - Fill in the article details

2. **SQL Query**:
   ```sql
   INSERT INTO articles (title, excerpt, author, image_url, url)
   VALUES (
       'Your Article Title',
       'A brief description of your article',
       'Author Name',
       'https://example.com/image.jpg',
       'https://example.com/article'
   );
   ```

### Customization

- **Colors**: Edit CSS variables in `styles.css` under `:root`
- **Layout**: Modify grid settings in `.articles-grid` and `.features`
- **Content**: Update text in `index.html`

## Security Notes

⚠️ **Important**: The Supabase anon key is safe to expose in client-side code ONLY because:
- Row Level Security (RLS) is enabled
- Public read access is granted via policies
- Write access requires authentication

For production applications with sensitive data, consider:
- Implementing user authentication
- Using server-side API routes
- Restricting RLS policies further

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT License - feel free to use this project for any purpose.

## Support

For issues or questions:
1. Check the browser console for errors
2. Verify Supabase credentials are correct
3. Ensure the articles table exists in your database
4. Check that RLS policies allow public read access
