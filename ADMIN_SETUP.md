# Admin Dashboard Setup Guide

## Overview

The admin dashboard allows you to create, manage, and delete articles through a secure web interface.

## Setup Steps

### 1. Run Database Setup

First, run the `setup.sql` script in your Supabase SQL Editor to create the articles table and set up the necessary policies.

### 2. Create an Admin User

You need to create an admin user account in Supabase:

#### Option A: Using Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** → **Users**
3. Click **Add user** → **Create new user**
4. Enter:
   - **Email**: Your admin email (e.g., `admin@handwerk.com`)
   - **Password**: A strong password
   - **Auto Confirm User**: ✓ (check this box)
5. Click **Create user**

#### Option B: Using Sign Up Page (Alternative)

If you want to enable public sign-ups, you can:

1. Enable email authentication in Supabase:
   - Go to **Authentication** → **Providers**
   - Enable **Email** provider
2. Create a sign-up form or use the Supabase Auth UI

### 3. Access the Admin Dashboard

1. Open `admin.html` in your browser
2. Sign in with your admin credentials
3. Start creating articles!

## Using the Admin Dashboard

### Creating Articles

1. **Title** (required): The main headline of your article
2. **Author**: Your name or pen name (defaults to "Anonymous")
3. **Excerpt**: A brief description (recommended ~150 characters) - shown on article cards
4. **Content**: The full article text (optional)
5. **Image URL**: Link to an image for the article card (optional)

### Managing Articles

- **Recent Articles**: View your 10 most recent articles
- **Delete**: Remove articles with the delete button
- Articles appear on the public site immediately after publishing

## Security Features

✅ **Authentication Required**: Only logged-in users can access the dashboard
✅ **Row Level Security**: Database policies prevent unauthorized access
✅ **XSS Protection**: All user input is sanitized
✅ **Session Management**: Automatic logout on session expiry

## Troubleshooting

### Can't Login?

- Verify your email and password are correct
- Check that the user exists in Supabase Authentication
- Ensure the user is confirmed (not pending)

### Articles Not Saving?

- Check browser console for errors
- Verify you're logged in
- Ensure database policies are set up correctly
- Check that the `articles` table exists

### Database Policies Not Working?

Make sure you ran the complete `setup.sql` script, including:
- `ENABLE ROW LEVEL SECURITY`
- All policy creation statements

## Tips

- Use high-quality images from free sources like [Unsplash](https://unsplash.com)
- Keep excerpts concise and engaging
- Preview your articles on the public site after publishing
- The `url` field is no longer used (articles don't link externally)

## Admin Credentials Storage

⚠️ **Important**: Never commit admin credentials to version control. Store them securely:
- Use a password manager
- Don't share credentials via email or chat
- Change passwords regularly
- Use strong, unique passwords

## Next Steps

Consider adding:
- Article editing functionality
- Rich text editor for content
- Image upload to Supabase Storage
- Article categories/tags
- Draft/publish status
- Article analytics
