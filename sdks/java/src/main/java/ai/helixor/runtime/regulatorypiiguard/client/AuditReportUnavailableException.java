package ai.helixor.runtime.regulatorypiiguard.client;

/**
 * The audit ledger exists only in the native C runtime (libhelixor_runtime),
 * which this client's HelixorNativeRuntime has not loaded.
 */
public class AuditReportUnavailableException extends IllegalStateException {
    public AuditReportUnavailableException(String message) {
        super(message);
    }
}
