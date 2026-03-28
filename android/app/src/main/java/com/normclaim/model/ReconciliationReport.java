package com.normclaim.model;

import java.util.List;

public class ReconciliationReport {
    public String documentId;
    public List<ReconciliationItem> matched;
    public List<ReconciliationItem> missed;
    public List<ReconciliationItem> extra;
    public Integer totalBilledCodes;
    public Integer totalExtractedCodes;
    public Double estimatedClaimDeltaInr;
    public Double confidence;
}
