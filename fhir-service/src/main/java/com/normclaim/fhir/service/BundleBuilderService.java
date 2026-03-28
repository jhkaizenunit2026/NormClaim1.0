package com.normclaim.fhir.service;

import com.normclaim.fhir.dto.DiagnosisDto;
import com.normclaim.fhir.dto.EncounterDto;
import com.normclaim.fhir.dto.ExtractionInputDto;
import com.normclaim.fhir.dto.MedicationDto;
import com.normclaim.fhir.dto.PatientDto;
import com.normclaim.fhir.dto.ProcedureDto;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.hl7.fhir.r4.model.Bundle;
import org.hl7.fhir.r4.model.Claim;
import org.hl7.fhir.r4.model.CodeableConcept;
import org.hl7.fhir.r4.model.Coding;
import org.hl7.fhir.r4.model.Condition;
import org.hl7.fhir.r4.model.DateTimeType;
import org.hl7.fhir.r4.model.Encounter;
import org.hl7.fhir.r4.model.Enumerations;
import org.hl7.fhir.r4.model.Extension;
import org.hl7.fhir.r4.model.HumanName;
import org.hl7.fhir.r4.model.Identifier;
import org.hl7.fhir.r4.model.MedicationRequest;
import org.hl7.fhir.r4.model.Meta;
import org.hl7.fhir.r4.model.Patient;
import org.hl7.fhir.r4.model.Period;
import org.hl7.fhir.r4.model.Procedure;
import org.hl7.fhir.r4.model.Reference;
import org.springframework.stereotype.Service;

@Service
public class BundleBuilderService {

  private static final String ICD10 = "http://hl7.org/fhir/sid/icd-10";
  private static final String RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm";
  private static final String SNOMED = "http://snomed.info/sct";
  private static final String CONSENT_EXT = "https://normclaim.io/fhir/StructureDefinition/consent-obtained";

  public Bundle build(ExtractionInputDto input) {
    Bundle bundle = new Bundle();
    bundle.setId(UUID.randomUUID().toString());
    bundle.setType(Bundle.BundleType.DOCUMENT);
    Meta meta = new Meta();
    meta.addProfile("https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle");
    bundle.setMeta(meta);

    String patientId = UUID.randomUUID().toString();
    String encounterId = UUID.randomUUID().toString();

    PatientDto p = input.getPatient() != null ? input.getPatient() : new PatientDto();
    EncounterDto e = input.getEncounter() != null ? input.getEncounter() : new EncounterDto();

    Patient patient = buildPatient(patientId, p);
    bundle.addEntry().setFullUrl("urn:uuid:" + patientId).setResource(patient);

    Encounter encounter = buildEncounter(encounterId, patientId, e);
    bundle.addEntry().setFullUrl("urn:uuid:" + encounterId).setResource(encounter);

    List<Claim.DiagnosisComponent> claimDiagnoses = new ArrayList<>();
    int seq = 1;
    List<DiagnosisDto> diagnoses = input.getDiagnoses() != null ? input.getDiagnoses() : List.of();
    for (DiagnosisDto d : diagnoses) {
      if (Boolean.TRUE.equals(d.getNegated())) {
        continue;
      }
      String condId = UUID.randomUUID().toString();
      Condition condition = buildCondition(condId, patientId, encounterId, d);
      bundle.addEntry().setFullUrl("urn:uuid:" + condId).setResource(condition);

      Claim.DiagnosisComponent dc = new Claim.DiagnosisComponent();
      dc.setSequence(seq++);
      String sys = d.getIcd10System() != null && !d.getIcd10System().isBlank() ? d.getIcd10System() : ICD10;
      String code = d.getIcd10Code() != null ? d.getIcd10Code() : "";
      String display = d.getIcd10Display() != null ? d.getIcd10Display() : d.getText();
      String text = d.getText() != null ? d.getText() : display;
      dc.setDiagnosis(toCodeableConcept(sys, code, display, text));
      claimDiagnoses.add(dc);
    }

    List<MedicationDto> meds = input.getMedications() != null ? input.getMedications() : List.of();
    for (MedicationDto m : meds) {
      String medId = UUID.randomUUID().toString();
      MedicationRequest mr = buildMedicationRequest(medId, patientId, encounterId, m);
      bundle.addEntry().setFullUrl("urn:uuid:" + medId).setResource(mr);
    }

    List<ProcedureDto> procs = input.getProcedures() != null ? input.getProcedures() : List.of();
    for (ProcedureDto pr : procs) {
      String procId = UUID.randomUUID().toString();
      Procedure procedure = buildProcedure(procId, patientId, encounterId, pr);
      bundle.addEntry().setFullUrl("urn:uuid:" + procId).setResource(procedure);
    }

    String claimId = UUID.randomUUID().toString();
    Claim claim = buildClaim(claimId, patientId, claimDiagnoses);
    bundle.addEntry().setFullUrl("urn:uuid:" + claimId).setResource(claim);

    return bundle;
  }

  private Patient buildPatient(String id, PatientDto p) {
    Patient patient = new Patient();
    patient.setId(id);
    patient.setActive(true);
    if (p.getName() != null && !p.getName().isBlank()) {
      HumanName hn = new HumanName();
      hn.setText(p.getName());
      patient.addName(hn);
    }
    if (p.getSex() != null && !p.getSex().isBlank()) {
      try {
        patient.setGender(Enumerations.AdministrativeGender.fromCode(p.getSex().toLowerCase()));
      } catch (Exception ignored) {
        // leave unset if not male/female/other/unknown
      }
    }
    if (p.getAbhaId() != null && !p.getAbhaId().isBlank()) {
      Identifier idAbha = new Identifier();
      idAbha.setSystem("https://healthid.ndhm.gov.in");
      idAbha.setValue(p.getAbhaId());
      patient.addIdentifier(idAbha);
    }
    Extension consent = new Extension();
    consent.setUrl(CONSENT_EXT);
    consent.setValue(new org.hl7.fhir.r4.model.BooleanType(false));
    patient.addExtension(consent);
    return patient;
  }

  private Encounter buildEncounter(String id, String patientId, EncounterDto e) {
    Encounter enc = new Encounter();
    enc.setId(id);
    enc.setStatus(Encounter.EncounterStatus.FINISHED);
    Encounter.EncounterClassComponent cc = new Encounter.EncounterClassComponent();
    cc.setSystem("http://terminology.hl7.org/CodeSystem/v3-ActCode");
    cc.setCode("IMP");
    cc.setDisplay("inpatient encounter");
    enc.setClass_(cc);
    enc.setSubject(new Reference("Patient/" + patientId));
    if ((e.getAdmitDate() != null && !e.getAdmitDate().isBlank())
        || (e.getDischargeDate() != null && !e.getDischargeDate().isBlank())) {
      Period period = new Period();
      if (e.getAdmitDate() != null && !e.getAdmitDate().isBlank()) {
        period.setStartElement(new DateTimeType(e.getAdmitDate()));
      }
      if (e.getDischargeDate() != null && !e.getDischargeDate().isBlank()) {
        period.setEndElement(new DateTimeType(e.getDischargeDate()));
      }
      enc.setPeriod(period);
    }
    return enc;
  }

  private Condition buildCondition(String id, String patientId, String encounterId, DiagnosisDto d) {
    Condition c = new Condition();
    c.setId(id);
    c.setClinicalStatus(
        new CodeableConcept()
            .addCoding(
                new Coding(
                    "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "active",
                    "Active")));
    c.setVerificationStatus(
        new CodeableConcept()
            .addCoding(
                new Coding(
                    "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "confirmed",
                    "Confirmed")));
    c.setSubject(new Reference("Patient/" + patientId));
    c.setEncounter(new Reference("Encounter/" + encounterId));
    String sys = d.getIcd10System() != null && !d.getIcd10System().isBlank() ? d.getIcd10System() : ICD10;
    String code = d.getIcd10Code() != null ? d.getIcd10Code() : "";
    String display = d.getIcd10Display() != null ? d.getIcd10Display() : d.getText();
    String text = d.getText() != null ? d.getText() : display;
    c.setCode(toCodeableConcept(sys, code, display, text));
    String note =
        String.format(
            "section=%s uncertainty=%s confidence=%s",
            nullToEmpty(d.getSection()),
            nullToEmpty(d.getUncertainty()),
            d.getConfidence() != null ? d.getConfidence() : 0.0);
    c.addNote().setText(note);
    return c;
  }

  private MedicationRequest buildMedicationRequest(
      String id, String patientId, String encounterId, MedicationDto m) {
    MedicationRequest mr = new MedicationRequest();
    mr.setId(id);
    mr.setStatus(MedicationRequest.MedicationRequestStatus.ACTIVE);
    mr.setIntent(MedicationRequest.MedicationRequestIntent.ORDER);
    mr.setSubject(new Reference("Patient/" + patientId));
    mr.setEncounter(new Reference("Encounter/" + encounterId));

    String generic =
        firstNonBlank(m.getGenericName(), m.getName(), m.getBrandName(), "Unknown medication");
    String brandOrName = firstNonBlank(m.getBrandName(), m.getName(), generic);
    String text =
        String.format(
            "%s | dose=%s route=%s frequency=%s duration=%s",
            brandOrName,
            nullToEmpty(m.getDose()),
            nullToEmpty(m.getRoute()),
            nullToEmpty(m.getFrequency()),
            nullToEmpty(m.getDuration()));

    CodeableConcept medCode = toCodeableConcept(SNOMED, generic.replace(' ', '-').toLowerCase(), generic, text);
    medCode.getCoding().add(new Coding().setSystem(RXNORM).setCode(generic).setDisplay(generic));
    mr.setMedication(medCode);
    return mr;
  }

  private Procedure buildProcedure(String id, String patientId, String encounterId, ProcedureDto p) {
    Procedure proc = new Procedure();
    proc.setId(id);
    proc.setStatus(Procedure.ProcedureStatus.COMPLETED);
    proc.setSubject(new Reference("Patient/" + patientId));
    proc.setEncounter(new Reference("Encounter/" + encounterId));
    proc.setCode(toCodeableConcept(SNOMED, "procedure", p.getText(), p.getText()));
    if (p.getDate() != null && !p.getDate().isBlank()) {
      proc.setPerformed(new DateTimeType(p.getDate()));
    }
    return proc;
  }

  private Claim buildClaim(String id, String patientId, List<Claim.DiagnosisComponent> diagnoses) {
    Claim claim = new Claim();
    claim.setId(id);
    claim.setStatus(Claim.ClaimStatus.ACTIVE);
    claim.setType(
        toCodeableConcept(
            "http://terminology.hl7.org/CodeSystem/claim-type",
            "institutional",
            "Institutional",
            "Institutional"));
    claim.setUse(Claim.Use.CLAIM);
    claim.setPatient(new Reference("Patient/" + patientId));
    for (Claim.DiagnosisComponent d : diagnoses) {
      claim.addDiagnosis(d);
    }
    return claim;
  }

  private static CodeableConcept toCodeableConcept(
      String system, String code, String display, String text) {
    CodeableConcept cc = new CodeableConcept();
    Coding coding = new Coding();
    coding.setSystem(system);
    coding.setCode(code);
    coding.setDisplay(display);
    cc.addCoding(coding);
    cc.setText(text);
    return cc;
  }

  private static String nullToEmpty(String s) {
    return s != null ? s : "";
  }

  private static String firstNonBlank(String... parts) {
    if (parts == null) {
      return "";
    }
    for (String p : parts) {
      if (p != null && !p.isBlank()) {
        return p;
      }
    }
    return "";
  }
}
