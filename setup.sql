-- Supabase Database Setup for Articles
-- Run this SQL in your Supabase SQL Editor

-- Create articles table
CREATE TABLE IF NOT EXISTS articles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    excerpt TEXT,
    content TEXT,
    author TEXT,
    image_url TEXT,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public read access
CREATE POLICY "Allow public read access" ON articles
    FOR SELECT
    TO anon
    USING (true);

-- Optional: Create policy for authenticated users to insert/update
CREATE POLICY "Allow authenticated users to insert" ON articles
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update" ON articles
    FOR UPDATE
    TO authenticated
    USING (true);

-- Insert sample articles (optional)
INSERT INTO articles (title, excerpt, author, image_url, url) VALUES
    (
        'Getting Started with Web Development',
        'Learn the fundamentals of modern web development including HTML, CSS, and JavaScript.',
        'John Doe',
        'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800',
        'https://example.com/article1'
    ),
    (
        'Introduction to Supabase',
        'Discover how Supabase can accelerate your application development with its powerful features.',
        'Jane Smith',
        'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800',
        'https://example.com/article2'
    ),
    (
        'Modern UI Design Principles',
        'Explore the key principles of creating beautiful and functional user interfaces.',
        'Alex Johnson',
        'https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800',
        'https://example.com/article3'
    );

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to call the function
CREATE TRIGGER update_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
