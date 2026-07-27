"""Unit tests for Korean job field enrichment heuristics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from job_field_enrichment import enrich_job_fields, infer_role, infer_seniority, infer_stack


class JobFieldEnrichment(unittest.TestCase):
    def test_junior_from_title(self):
        sen, _ = infer_seniority("[네이버] 신입 백엔드 개발자 채용")
        self.assertEqual(sen, "신입")

    def test_experienced_from_title(self):
        sen, note = infer_seniority("경력사원 채용 (시스템 운영/개발)", "경력 3–5년")
        self.assertEqual(sen, "경력")
        self.assertTrue(note)

    def test_either(self):
        sen, _ = infer_seniority("백엔드 개발자 (신입/경력)")
        self.assertEqual(sen, "신입·경력")

    def test_backend_vs_frontend(self):
        self.assertEqual(infer_role("백엔드 개발자 (Java/Spring)", "백엔드 개발자 (Java/Spring)"), "백엔드")
        self.assertEqual(infer_role("Frontend Engineer — React", "Frontend Engineer — React"), "프론트엔드")
        self.assertEqual(infer_role("풀스택 개발자", "풀스택 개발자"), "풀스택")

    def test_title_backend_wins_over_infra_keywords_in_body(self):
        role = infer_role(
            "AWS, Docker, Kubernetes 경험자 우대",
            title="콘텐츠 플랫폼 백엔드 개발 (Junior)",
        )
        self.assertEqual(role, "백엔드")

    def test_recruiter_is_non_dev(self):
        self.assertEqual(infer_role("채용 담당자(helper recruiter) 모집", "채용 담당자(helper recruiter) 모집"), "비개발")

    def test_experienced_title_beats_intern_in_body(self):
        sen, _ = infer_seniority(
            "본 공고와 별도로 인턴 채용도 진행 중입니다",
            title="[네이버웹툰] 백엔드 서버 개발 (경력)",
        )
        self.assertEqual(sen, "경력")

    def test_explicit_skills_list(self):
        fields = enrich_job_fields(
            title="백엔드 개발자",
            description="",
            skills=["JAVA", "Spring Boot", "AWS"],
        )
        self.assertEqual(fields["role"], "백엔드")
        self.assertIn("Java", fields["stack"])
        self.assertIn("Spring", fields["stack"])
        self.assertIn("AWS", fields["stack"])

    def test_stack_extraction(self):
        stack = infer_stack("자격요건: Java, Spring Boot, AWS, Kubernetes 경험")
        self.assertIn("Java", stack)
        self.assertIn("Spring", stack)
        self.assertIn("AWS", stack)
        self.assertIn("Kubernetes", stack)

    def test_enrich_merges(self):
        fields = enrich_job_fields(
            title="신입 프론트엔드 개발자",
            description="React, TypeScript 필수",
        )
        self.assertEqual(fields["seniority"], "신입")
        self.assertEqual(fields["role"], "프론트엔드")
        self.assertIn("React", fields["stack"])
        self.assertIn("TypeScript", fields["stack"])


if __name__ == "__main__":
    unittest.main()
