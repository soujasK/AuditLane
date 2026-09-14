from __future__ import annotations

import tempfile
from pathlib import Path
from auditlane.attestation import (
    create_voice_attestation,
    save_attestation,
    load_attestation,
    VoiceAttestation,
)


def test_attestation_signature_validates_successfully():
    attest = create_voice_attestation(
        commit_sha="7f9c2a1e80",
        pr_reference="acme/repo#42",
        authorizer_name="@sarah_dba",
        phone_number="+14155550192",
        statement="Yes, I authorized this change in standup.",
        entailment_score=0.91,
        verdict="VERIFIED",
    )
    assert attest.verify() is True
    assert attest.signature.startswith("sig:hmac-sha256:")
    assert attest.authorizer_phone_masked.startswith("+14")


def test_tampered_attestation_fails_verification():
    attest = create_voice_attestation(
        commit_sha="7f9c2a1e80",
        pr_reference="acme/repo#42",
        authorizer_name="@sarah_dba",
        phone_number="+14155550192",
        statement="Original statement",
        entailment_score=0.91,
        verdict="VERIFIED",
    )
    # Tamper with the statement
    attest.authorizer_statement = "Tampered fraudulent statement"
    assert attest.verify() is False


def test_save_and_load_attestation_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        attest = create_voice_attestation(
            commit_sha="abc1234567",
            pr_reference="acme/repo#100",
            authorizer_name="The architect",
            phone_number="+12065550148",
            statement="Signed off on this change.",
            verdict="VERIFIED",
        )
        saved_file = save_attestation(attest, base_dir=tmp_path)
        assert saved_file.exists()

        loaded = load_attestation("abc1234567", base_dir=tmp_path)
        assert loaded is not None
        assert loaded.attestation_id == attest.attestation_id
        assert loaded.commit_sha == "abc1234567"
        assert loaded.verify() is True
