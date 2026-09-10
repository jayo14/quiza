import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://spenbgerufkzhuzfwmoi.supabase.co";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNwZW5iZ2VydWZremh1emZ3bW9pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1MzkyNzksImV4cCI6MjEwNDExNTI3OX0.zzLAFq30X_kQb4BjHa8HgstST7uDBpd6l6EAa8zC5uM";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
