"""The golden set: input -> expected action and rule IDs, in order.

From the "Testing policies" tutorial: https://helixor.dev/tutorials/testing-policies.html
Keep this file free of real data; use the standard test values.
"""

import pytest

# pytest.param(input, expected action, expected rule ids, id=...)
GOLDEN = [
    pytest.param("Move the design review to Thursday.",
                 "permit_clean_payload", [], id="clean"),
    pytest.param("Send the deck to dana.reyes@example.com.",
                 "redact_and_permit_contact_pii", ["RULE-GDPR-EMAIL-REDACT"], id="email"),
    pytest.param("Call the front desk at (415) 555-0100.",
                 "redact_and_permit_contact_pii", ["RULE-TCPA-PHONE-REDACT"], id="phone"),
    pytest.param("Request came from 192.168.10.24 overnight.",
                 "redact_and_permit_contact_pii", ["RULE-GDPR-IP-REDACT"], id="ipv4"),
    pytest.param("Email ops@example.com or call (212) 555-0199.",
                 "redact_and_permit_contact_pii",
                 ["RULE-GDPR-EMAIL-REDACT", "RULE-TCPA-PHONE-REDACT"], id="email+phone"),
    pytest.param("Applicant SSN 123-45-6789 verified.",
                 "block_glba_ssn_leakage", ["RULE-GLBA-SSN-BLOCK"], id="ssn"),
    pytest.param("Card 4111-1111-1111-1111 on file.",
                 "block_pci_dss_pan_leakage", ["RULE-PCI-DSS-PAN-BLOCK"], id="card"),
    pytest.param("Chart MRN-1234567 attached.",
                 "block_hipaa_phi_leakage", ["RULE-HIPAA-PHI-BLOCK"], id="health-id"),
    # Precedence: the first fatal rule decides; every match is reported.
    pytest.param("Card 4111-1111-1111-1111, receipt to jane@example.com.",
                 "block_pci_dss_pan_leakage", ["RULE-PCI-DSS-PAN-BLOCK", "RULE-GDPR-EMAIL-REDACT"],
                 id="card+email"),
    # Near misses that must stay clean.
    pytest.param("Order 4111-1111-1111-1112 shipped.",
                 "permit_clean_payload", [], id="fails-luhn"),
    pytest.param("Extension 555-0100 is the lobby.",
                 "permit_clean_payload", [], id="seven-digit-number"),
]
