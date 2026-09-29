package ai.helixor.runtime.regulatorypiiguard.model;

import java.io.Serializable;

/**
 * Strongly-typed domain entity state for compliance.regulatory_pii_guard.v1.
 */
public record RegulatoryPiiGuardState(
    boolean hasSsn,
    boolean hasCreditCard,
    boolean hasHealthRecord,
    boolean hasPhone,
    boolean hasIp,
    boolean hasEmail
) implements Serializable {

    public static Builder builder() {
        return new Builder();
    }

    public String toJson() {
        StringBuilder sb = new StringBuilder("{");
            sb.append("\"has_ssn\":" + hasSsn + ",");
            sb.append("\"has_credit_card\":" + hasCreditCard + ",");
            sb.append("\"has_health_record\":" + hasHealthRecord + ",");
            sb.append("\"has_phone\":" + hasPhone + ",");
            sb.append("\"has_ip\":" + hasIp + ",");
            sb.append("\"has_email\":" + hasEmail + ",");
        if (sb.charAt(sb.length() - 1) == ',') {
            sb.deleteCharAt(sb.length() - 1);
        }
        sb.append("}");
        return sb.toString();
    }

    public static final class Builder {
        private boolean hasSsn;
        private boolean hasCreditCard;
        private boolean hasHealthRecord;
        private boolean hasPhone;
        private boolean hasIp;
        private boolean hasEmail;

        public Builder hasSsn(boolean hasSsn) {
            this.hasSsn = hasSsn;
            return this;
        }
        public Builder hasCreditCard(boolean hasCreditCard) {
            this.hasCreditCard = hasCreditCard;
            return this;
        }
        public Builder hasHealthRecord(boolean hasHealthRecord) {
            this.hasHealthRecord = hasHealthRecord;
            return this;
        }
        public Builder hasPhone(boolean hasPhone) {
            this.hasPhone = hasPhone;
            return this;
        }
        public Builder hasIp(boolean hasIp) {
            this.hasIp = hasIp;
            return this;
        }
        public Builder hasEmail(boolean hasEmail) {
            this.hasEmail = hasEmail;
            return this;
        }

        public RegulatoryPiiGuardState build() {
            return new RegulatoryPiiGuardState(hasSsn, hasCreditCard, hasHealthRecord, hasPhone, hasIp, hasEmail);
        }
    }
}
