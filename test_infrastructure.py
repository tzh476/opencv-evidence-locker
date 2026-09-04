import unittest
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # The production Lambda image intentionally omits test-only PyYAML.
    yaml = None


ROOT = Path(__file__).parent


@unittest.skipIf(yaml is None, "PyYAML is only required for local infrastructure validation")
class InfrastructureTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = yaml.safe_load((ROOT / "template.yaml").read_text())
        cls.resources = cls.template["Resources"]

    def test_template_is_sam_and_uses_an_arm64_image(self) -> None:
        self.assertEqual(self.template["Transform"], "AWS::Serverless-2016-10-31")
        function = self.resources["EvidenceFunction"]
        self.assertEqual(function["Type"], "AWS::Serverless::Function")
        self.assertEqual(function["Properties"]["PackageType"], "Image")
        self.assertEqual(function["Properties"]["Architectures"], ["arm64"])
        self.assertEqual(function["Metadata"]["Dockerfile"], "Dockerfile")

    def test_compute_and_storage_are_bounded(self) -> None:
        properties = self.resources["EvidenceFunction"]["Properties"]
        self.assertLessEqual(properties["Timeout"], 120)
        self.assertLessEqual(properties["ReservedConcurrentExecutions"], 2)
        self.assertLessEqual(properties["EphemeralStorage"]["Size"], 2048)
        retention = self.template["Parameters"]["ArtifactRetentionDays"]
        self.assertEqual(retention["Default"], 7)
        self.assertLessEqual(retention["MaxValue"], 30)

    def test_buckets_are_private_encrypted_and_expiring(self) -> None:
        for name in ("InputBucket", "EvidenceBucket"):
            properties = self.resources[name]["Properties"]
            encryption = properties["BucketEncryption"]["ServerSideEncryptionConfiguration"]
            self.assertEqual(encryption[0]["ServerSideEncryptionByDefault"]["SSEAlgorithm"], "AES256")
            public = properties["PublicAccessBlockConfiguration"]
            self.assertTrue(all(public.values()))
            expiry = properties["LifecycleConfiguration"]["Rules"][0]["ExpirationInDays"]
            self.assertEqual(expiry, {"Ref": "ArtifactRetentionDays"})

    def test_event_is_restricted_to_incoming_mp4_files(self) -> None:
        event = self.resources["EvidenceFunction"]["Properties"]["Events"]["UploadedVideo"]
        self.assertEqual(event["Type"], "S3")
        rules = event["Properties"]["Filter"]["S3Key"]["Rules"]
        self.assertEqual(rules, [
            {"Name": "prefix", "Value": "incoming/"},
            {"Name": "suffix", "Value": ".mp4"},
        ])

    def test_function_has_only_required_bucket_policies(self) -> None:
        policies = self.resources["EvidenceFunction"]["Properties"]["Policies"]
        self.assertEqual(policies, [
            {"S3ReadPolicy": {"BucketName": {"Ref": "InputBucket"}}},
            {"S3WritePolicy": {"BucketName": {"Ref": "EvidenceBucket"}}},
        ])


if __name__ == "__main__":
    unittest.main()
