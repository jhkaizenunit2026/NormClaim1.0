package com.normclaim.fhir.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ExtractionInputDto {

  private String documentId;
  private PatientDto patient;
  private EncounterDto encounter;
  private List<DiagnosisDto> diagnoses;
  private List<ProcedureDto> procedures;
  private List<MedicationDto> medications;

  public String getDocumentId() {
    return documentId;
  }

  public void setDocumentId(String documentId) {
    this.documentId = documentId;
  }

  public PatientDto getPatient() {
    return patient;
  }

  public void setPatient(PatientDto patient) {
    this.patient = patient;
  }

  public EncounterDto getEncounter() {
    return encounter;
  }

  public void setEncounter(EncounterDto encounter) {
    this.encounter = encounter;
  }

  public List<DiagnosisDto> getDiagnoses() {
    return diagnoses;
  }

  public void setDiagnoses(List<DiagnosisDto> diagnoses) {
    this.diagnoses = diagnoses;
  }

  public List<ProcedureDto> getProcedures() {
    return procedures;
  }

  public void setProcedures(List<ProcedureDto> procedures) {
    this.procedures = procedures;
  }

  public List<MedicationDto> getMedications() {
    return medications;
  }

  public void setMedications(List<MedicationDto> medications) {
    this.medications = medications;
  }
}
