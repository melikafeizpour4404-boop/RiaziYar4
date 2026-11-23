-- Run this entire file in Supabase SQL Editor.
create extension if not exists pgcrypto;

create table if not exists public.schools (
  id uuid primary key,
  name text not null,
  city text default '',
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.classes (
  id uuid primary key,
  school_id uuid not null references public.schools(id) on delete cascade,
  name text not null,
  grade text not null default 'هشتم',
  unique(school_id,name)
);

create table if not exists public.users (
  id uuid primary key,
  username text not null unique,
  full_name text not null,
  password_hash text not null,
  role text not null check (role in ('designer','school_admin','teacher','student')),
  school_id uuid references public.schools(id) on delete cascade,
  class_id uuid references public.classes(id) on delete set null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.materials (
  id uuid primary key,
  school_id uuid not null references public.schools(id) on delete cascade,
  class_id uuid references public.classes(id) on delete cascade,
  title text not null,
  chapter text default '',
  storage_path text not null,
  original_name text not null,
  uploaded_by uuid not null references public.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.grades (
  id uuid primary key,
  school_id uuid not null references public.schools(id) on delete cascade,
  student_id uuid not null references public.users(id),
  teacher_id uuid not null references public.users(id),
  subject text not null,
  assessment text not null,
  score numeric(5,2) not null check(score >= 0 and score <= 20),
  created_at timestamptz not null default now()
);

-- Private file bucket. Do not make it public.
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
values ('learning-files','learning-files',false,104857600,
array['application/pdf','video/mp4','video/quicktime','image/png','image/jpeg',
'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
'application/vnd.openxmlformats-officedocument.presentationml.presentation'])
on conflict (id) do update set public=false;

-- This starter uses the Supabase service-role key only on the server.
-- Never put that key in browser code, public repositories, or user-visible files.
-- For a production deployment, replace service-role database access with
-- authenticated Supabase Auth + Row Level Security policies and audited RPCs.
