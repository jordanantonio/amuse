CREATE EXTENSION IF NOT EXISTS btree_gist;
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='shift_app') THEN
    CREATE ROLE shift_app NOLOGIN NOSUPERUSER NOBYPASSRLS;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO shift_app;
-- Application tables are accessed only by the server's restricted group role.
-- Supabase's browser roles must not get direct access, including default grants.
REVOKE ALL ON TABLE public.organizations, public.memberships, public.workers,
  public.worker_skills, public.certifications, public.availability_windows,
  public.private_commitments, public.worker_absences, public.worksites,
  public.projects, public.tasks, public.task_dependencies, public.assignments,
  public.job_postings, public.applications, public.schedule_drafts,
  public.invitations, public.audit_events FROM PUBLIC;
DO $$ DECLARE role_name text; BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT FROM pg_roles WHERE rolname=role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.organizations, public.memberships, public.workers,
        public.worker_skills, public.certifications, public.availability_windows,
        public.private_commitments, public.worker_absences, public.worksites,
        public.projects, public.tasks, public.task_dependencies, public.assignments,
        public.job_postings, public.applications, public.schedule_drafts,
        public.invitations, public.audit_events FROM %I', role_name);
    END IF;
  END LOOP;
END $$;

-- Definer functions belong to the migration owner, never the runtime role.
-- All names are schema qualified and search_path excludes writable schemas.
CREATE FUNCTION public.shift_actor()
RETURNS TABLE(id text, organization_id text, role text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT m.id::text, m.organization_id::text, m.role::text FROM public.memberships m
  WHERE m.auth_subject = nullif(current_setting('shift.subject', true), '')
$$;
CREATE FUNCTION public.shift_worker_visible(worker text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT EXISTS(SELECT 1 FROM public.workers w, public.shift_actor() a
    WHERE w.id=worker AND w.organization_id=a.organization_id
      AND (a.role IN ('manager','admin') OR w.membership_id=a.id))
$$;
CREATE FUNCTION public.shift_project_managed(project text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT EXISTS(SELECT 1 FROM public.projects p, public.shift_actor() a
    WHERE p.id=project AND p.organization_id=a.organization_id
      AND (a.role='admin' OR (a.role='manager' AND p.manager_id=a.id)))
$$;
CREATE FUNCTION public.shift_project_visible(project text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT public.shift_project_managed(project) OR EXISTS(
    SELECT 1 FROM public.assignments s JOIN public.tasks t ON t.id=s.task_id
      JOIN public.workers w ON w.id=s.worker_id
      JOIN public.projects p ON p.id=t.project_id, public.shift_actor() a
    WHERE t.project_id=project AND a.role='worker' AND w.membership_id=a.id
      AND p.organization_id=a.organization_id AND w.organization_id=a.organization_id)
$$;
CREATE FUNCTION public.shift_busy()
RETURNS TABLE(id text, worker_id text, starts_at timestamptz, ends_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT c.id::text, c.worker_id::text, c.starts_at, c.ends_at
    FROM public.private_commitments c WHERE public.shift_worker_visible(c.worker_id)
  UNION ALL
  SELECT c.id::text, c.worker_id::text, c.starts_at, c.ends_at
    FROM public.worker_absences c WHERE public.shift_worker_visible(c.worker_id)
  UNION ALL
  SELECT s.id::text, s.worker_id::text, s.starts_at, s.ends_at
    FROM public.assignments s JOIN public.tasks t ON t.id=s.task_id
    WHERE s.status='confirmed' AND public.shift_worker_visible(s.worker_id)
      AND NOT public.shift_project_visible(t.project_id)
$$;
CREATE FUNCTION public.shift_external_commitments(project text)
RETURNS TABLE(id text, worker_id text, starts_at timestamptz, ends_at timestamptz,
              same_site boolean, onsite boolean)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT s.id::text, s.worker_id::text, s.starts_at, s.ends_at,
         p.worksite_id=target.worksite_id, t.work_mode <> 'remote'
  FROM public.assignments s JOIN public.tasks t ON t.id=s.task_id
    JOIN public.projects p ON p.id=t.project_id
    JOIN public.projects target ON target.id=project
  WHERE public.shift_project_managed(project) AND s.status='confirmed'
    AND p.organization_id=target.organization_id AND t.project_id <> project
$$;

DO $$ DECLARE tbl text; BEGIN
  FOREACH tbl IN ARRAY ARRAY['organizations','memberships','workers','worker_skills',
    'certifications','availability_windows','private_commitments','worker_absences',
    'worksites','projects','tasks','task_dependencies','assignments','job_postings',
    'applications','schedule_drafts','invitations','audit_events'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format('GRANT SELECT ON public.%I TO shift_app', tbl);
  END LOOP;
END $$;
CREATE POLICY shift_read ON public.organizations FOR SELECT TO shift_app
  USING (id IN (SELECT organization_id FROM public.shift_actor()));
CREATE POLICY shift_read ON public.memberships FOR SELECT TO shift_app
  USING (auth_subject=nullif(current_setting('shift.subject',true),''));
CREATE POLICY shift_read ON public.workers FOR SELECT TO shift_app
  USING (public.shift_worker_visible(id));
CREATE POLICY shift_read ON public.worker_skills FOR SELECT TO shift_app
  USING (public.shift_worker_visible(worker_id));
CREATE POLICY shift_read ON public.certifications FOR SELECT TO shift_app
  USING (public.shift_worker_visible(worker_id));
CREATE POLICY shift_read ON public.availability_windows FOR SELECT TO shift_app
  USING (public.shift_worker_visible(worker_id));
CREATE POLICY shift_read ON public.private_commitments FOR SELECT TO shift_app
  USING (worker_id IN (SELECT w.id FROM public.workers w, public.shift_actor() a
    WHERE w.membership_id=a.id));
CREATE POLICY shift_read ON public.worker_absences FOR SELECT TO shift_app
  USING (public.shift_worker_visible(worker_id));
CREATE POLICY shift_read ON public.worksites FOR SELECT TO shift_app
  USING (organization_id IN (SELECT organization_id FROM public.shift_actor()));
CREATE POLICY shift_read ON public.projects FOR SELECT TO shift_app
  USING (public.shift_project_visible(id));
CREATE POLICY shift_read ON public.tasks FOR SELECT TO shift_app
  USING (public.shift_project_visible(project_id));
CREATE POLICY shift_read ON public.task_dependencies FOR SELECT TO shift_app
  USING (task_id IN (SELECT id FROM public.tasks) AND predecessor_id IN (SELECT id FROM public.tasks));
CREATE POLICY shift_read ON public.assignments FOR SELECT TO shift_app
  USING (EXISTS(SELECT 1 FROM public.tasks t WHERE t.id=task_id
    AND public.shift_project_managed(t.project_id))
    OR worker_id IN (SELECT w.id FROM public.workers w, public.shift_actor() a WHERE w.membership_id=a.id));
CREATE POLICY shift_read ON public.job_postings FOR SELECT TO shift_app
  USING (organization_id IN (SELECT organization_id FROM public.shift_actor()));
CREATE POLICY shift_read ON public.applications FOR SELECT TO shift_app
  USING (worker_id IN (SELECT w.id FROM public.workers w, public.shift_actor() a WHERE w.membership_id=a.id)
    OR job_id IN (SELECT j.id FROM public.job_postings j WHERE public.shift_project_managed(j.project_id)));
CREATE POLICY shift_read ON public.schedule_drafts FOR SELECT TO shift_app
  USING (public.shift_project_managed(project_id));
CREATE POLICY shift_read ON public.invitations FOR SELECT TO shift_app
  USING (worker_id IN (SELECT w.id FROM public.workers w, public.shift_actor() a WHERE w.membership_id=a.id)
    OR draft_id IN (SELECT id FROM public.schedule_drafts));
CREATE POLICY shift_read ON public.audit_events FOR SELECT TO shift_app
  USING (actor_id IN (SELECT id FROM public.shift_actor()));

-- Only currently implemented mutations receive grants. No assignment creation,
-- membership editing, or approval/acceptance is available to runtime credentials.
GRANT INSERT ON public.schedule_drafts, public.worker_absences, public.audit_events TO shift_app;
GRANT UPDATE(status) ON public.assignments TO shift_app;
CREATE POLICY shift_insert ON public.schedule_drafts FOR INSERT TO shift_app
  WITH CHECK (public.shift_project_managed(project_id) AND status='draft'
    AND created_by IN (SELECT id FROM public.shift_actor()));
CREATE POLICY shift_insert ON public.worker_absences FOR INSERT TO shift_app
  WITH CHECK (public.shift_worker_visible(worker_id)
    AND recorded_by IN (SELECT id FROM public.shift_actor() WHERE role IN ('manager','admin')));
CREATE POLICY shift_insert ON public.audit_events FOR INSERT TO shift_app
  WITH CHECK (actor_id IN (SELECT id FROM public.shift_actor() WHERE organization_id=audit_events.organization_id));
CREATE POLICY shift_update ON public.assignments FOR UPDATE TO shift_app
  USING (status='confirmed' AND task_id IN (SELECT id FROM public.tasks WHERE public.shift_project_managed(project_id)))
  WITH CHECK (status='disrupted' AND task_id IN (SELECT id FROM public.tasks WHERE public.shift_project_managed(project_id)));

ALTER TABLE public.assignments ADD CONSTRAINT assignments_no_confirmed_overlap
  EXCLUDE USING gist (worker_id WITH =, tstzrange(starts_at,ends_at,'[)') WITH &&)
  WHERE (status='confirmed');

DO $$ DECLARE signature text; BEGIN
  FOREACH signature IN ARRAY ARRAY['shift_actor()', 'shift_worker_visible(text)',
    'shift_project_managed(text)', 'shift_project_visible(text)', 'shift_busy()',
    'shift_external_commitments(text)'] LOOP
    EXECUTE 'REVOKE ALL ON FUNCTION public.' || signature || ' FROM PUBLIC';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.' || signature || ' TO shift_app';
  END LOOP;
END $$;
