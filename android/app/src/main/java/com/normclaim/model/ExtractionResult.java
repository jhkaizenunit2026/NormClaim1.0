package com.normclaim.model;

import java.util.List;

public class ExtractionResult {
    public String documentId;
    public PatientInfo patient;
    public EncounterInfo encounter;
    public List<Diagnosis> diagnoses;
    public List<Medication> medications;
    public List<String> billedCodes;
    public String rawTextPreview;
}
