from caregent_etl.extract import extract_jobs
from caregent_etl.transform import extract_skills, transform_jobs


def test_extract_skills_uses_canonical_names():
    text = "Apache Airflow, Python, PostgreSQL, AWS, Docker"

    assert extract_skills(text) == ["airflow", "aws", "docker", "postgresql", "python"]


def test_transform_deduplicates_by_source_id_and_builds_trends():
    payload = transform_jobs(extract_jobs())

    assert len(payload["jobs"]) == 4
    assert payload["trends"]

    trends = {trend["skill_name"]: trend for trend in payload["trends"]}
    assert trends["python"]["frequency"] == 3
    assert trends["aws"]["frequency"] == 2
    assert trends["airflow"]["frequency"] == 2
    assert trends["python"]["trend_score"] == 1.0


def test_transform_classifies_data_engineering_and_industry():
    payload = transform_jobs(extract_jobs())
    jobs_by_company = {job["company_name"]: job for job in payload["jobs"]}

    assert jobs_by_company["Hanbit Data"]["category"] == "data_engineer"
    assert jobs_by_company["Mirae Semiconductor"]["industry"] == "semiconductor"
