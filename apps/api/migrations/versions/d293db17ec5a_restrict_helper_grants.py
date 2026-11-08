"""Remove Supabase default browser grants from scheduling helper functions."""

from alembic import op

revision = "d293db17ec5a"
down_revision = "c8422af013ab"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
      DO $$ DECLARE role_name text; signature text; BEGIN
        FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
          IF EXISTS (SELECT FROM pg_roles WHERE rolname=role_name) THEN
            FOREACH signature IN ARRAY ARRAY['shift_actor()', 'shift_worker_visible(text)',
              'shift_project_managed(text)', 'shift_project_visible(text)', 'shift_busy()',
              'shift_external_commitments(text)'] LOOP
              EXECUTE format('REVOKE ALL ON FUNCTION public.%s FROM %I', signature, role_name);
            END LOOP;
          END IF;
        END LOOP;
      END $$;
    """)


def downgrade():
    # Never restore excessive browser grants. The preceding migration drops helpers.
    pass
