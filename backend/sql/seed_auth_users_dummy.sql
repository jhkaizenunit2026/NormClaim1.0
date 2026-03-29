-- Seed auth.users (+ auth.identities) for dummy_data CSVs (profiles.csv / patients.csv FKs).
-- Run in Supabase SQL Editor (or psql with access to auth schema).
--
-- Password for all three accounts: DummyPassword123!
-- Change raw_user_meta_data / emails to suit your project.
--
-- If public.profiles rows already exist for these ids (e.g. from CSV), either:
--   DELETE FROM public.profiles WHERE id IN (...);  -- before running, OR
--   Skip profiles.csv import and rely on handle_new_user() + UPDATE profiles below.
--
-- To re-run after a failed partial insert, delete in this order (dev only):
--   DELETE FROM auth.identities WHERE user_id IN (
--     '10000000-0000-0000-0000-000000000001'::uuid,
--     '10000000-0000-0000-0000-000000000002'::uuid,
--     '10000000-0000-0000-0000-000000000003'::uuid,
--   );
--   DELETE FROM auth.users WHERE id IN (same ids as above);

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
DECLARE
  -- auth.instances is often empty (local / fresh projects). GoTrue defaults instance_id to nil UUID.
  -- If INSERT fails on instance_id FK, inspect auth.instances and insert the required row, or use the id from SELECT id FROM auth.instances LIMIT 1 after creating a user in the Dashboard once.
  v_instance UUID := COALESCE(
    (SELECT id FROM auth.instances LIMIT 1),
    '00000000-0000-0000-0000-000000000000'::uuid
  );
  v_pw TEXT := crypt('DummyPassword123!', gen_salt('bf'));
BEGIN
  -- 1) Hospital admin — matches profiles.csv row 1
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at, confirmation_token, email_change, email_change_token_new, recovery_token
  ) VALUES (
    '10000000-0000-0000-0000-000000000001'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'hospital.admin@example.com',
    v_pw,
    NOW(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"name":"City General Admin","role":"HOSPITAL"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', ''
  );

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '10000000-0000-0000-0000-000000000001'::uuid,
    '10000000-0000-0000-0000-000000000001'::uuid,
    jsonb_build_object(
      'sub', '10000000-0000-0000-0000-000000000001',
      'email', 'hospital.admin@example.com',
      'email_verified', true
    ),
    'email',
    '10000000-0000-0000-0000-000000000001'::text,
    NOW(), NOW(), NOW()
  );

  -- 2) TPA — matches profiles.csv row 2
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at, confirmation_token, email_change, email_change_token_new, recovery_token
  ) VALUES (
    '10000000-0000-0000-0000-000000000002'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'tpa.reviewer@example.com',
    v_pw,
    NOW(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"name":"TPA Reviewer One","role":"TPA"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', ''
  );

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '10000000-0000-0000-0000-000000000002'::uuid,
    '10000000-0000-0000-0000-000000000002'::uuid,
    jsonb_build_object(
      'sub', '10000000-0000-0000-0000-000000000002',
      'email', 'tpa.reviewer@example.com',
      'email_verified', true
    ),
    'email',
    '10000000-0000-0000-0000-000000000002'::text,
    NOW(), NOW(), NOW()
  );

  -- 3) Finance — matches profiles.csv row 3
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at, confirmation_token, email_change, email_change_token_new, recovery_token
  ) VALUES (
    '10000000-0000-0000-0000-000000000003'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'finance.ops@example.com',
    v_pw,
    NOW(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"name":"Finance Ops","role":"FINANCE"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', ''
  );

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '10000000-0000-0000-0000-000000000003'::uuid,
    '10000000-0000-0000-0000-000000000003'::uuid,
    jsonb_build_object(
      'sub', '10000000-0000-0000-0000-000000000003',
      'email', 'finance.ops@example.com',
      'email_verified', true
    ),
    'email',
    '10000000-0000-0000-0000-000000000003'::text,
    NOW(), NOW(), NOW()
  );
END $$;

-- Optional: align public.profiles with dummy_data/profiles.csv (extra columns)
UPDATE public.profiles SET
  hospital_id = 'HOSP-001',
  tpa_officer_id = NULL,
  finance_user_id = NULL,
  avatar_url = 'https://example.com/avatars/h1.png'
WHERE id = '10000000-0000-0000-0000-000000000001'::uuid;

UPDATE public.profiles SET
  hospital_id = NULL,
  tpa_officer_id = 'TPA-OFF-22',
  finance_user_id = NULL,
  avatar_url = 'https://example.com/avatars/t1.png'
WHERE id = '10000000-0000-0000-0000-000000000002'::uuid;

UPDATE public.profiles SET
  hospital_id = NULL,
  tpa_officer_id = NULL,
  finance_user_id = NULL,
  avatar_url = 'https://example.com/avatars/f1.png'
WHERE id = '10000000-0000-0000-0000-000000000003'::uuid;
