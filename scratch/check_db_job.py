import psycopg

db_url = "postgres://postgres:sW4BToE1PaHEtVaNRuGb6962DsNAp2r-@junction.proxy.rlwy.net:20463/railway"
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM proposal_jobs WHERE id = 'job_c7f9b43a11e5';")
        print("Job row:", cur.fetchall())
        cur.execute("SELECT * FROM proposal_runs WHERE job_id = 'job_c7f9b43a11e5';")
        print("Run rows:", cur.fetchall())
        cur.execute("SELECT count(*) FROM proposal_jobs;")
        print("Total proposal_jobs:", cur.fetchone())
        cur.execute("SELECT id, status, created_at FROM proposal_jobs ORDER BY created_at DESC LIMIT 3;")
        print("Latest jobs:", cur.fetchall())
