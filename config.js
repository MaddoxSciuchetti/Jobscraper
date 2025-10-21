// Supabase Configuration
// IMPORTANT: In production, use environment variables or a secure backend
// Never expose your Supabase anon key in client-side code for sensitive data

const SUPABASE_CONFIG = {
    url: 'https://vahqqqmmwhpxdlgfpfpe.supabase.co',
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZhaHFxcW1td2hweGRsZ2ZwZnBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA5OTM2MjIsImV4cCI6MjA3NjU2OTYyMn0.gcTEFIrMje3ql_5dpcNtsGN934ujbFZU4-NaWso-I6k'
};

// Initialize Supabase client
const supabase = window.supabase.createClient(
    SUPABASE_CONFIG.url,
    SUPABASE_CONFIG.anonKey
);
