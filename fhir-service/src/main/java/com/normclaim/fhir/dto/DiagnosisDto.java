package com.normclaim.fhir.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class DiagnosisDto {

  private String text;
  private String icd10Code;
  private String icd10System;
  private String icd10Display;
  private Boolean isPrimary;
  private Double confidence;
  private Boolean negated;
  private String uncertainty;
  private String section;

  public String getText() {
    return text;
  }

  public void setText(String text) {
    this.text = text;
  }

  public String getIcd10Code() {
    return icd10Code;
  }

  public void setIcd10Code(String icd10Code) {
    this.icd10Code = icd10Code;
  }

  public String getIcd10System() {
    return icd10System;
  }

  public void setIcd10System(String icd10System) {
    this.icd10System = icd10System;
  }

  public String getIcd10Display() {
    return icd10Display;
  }

  public void setIcd10Display(String icd10Display) {
    this.icd10Display = icd10Display;
  }

  public Boolean getIsPrimary() {
    return isPrimary;
  }

  public void setIsPrimary(Boolean primary) {
    isPrimary = primary;
  }

  public Double getConfidence() {
    return confidence;
  }

  public void setConfidence(Double confidence) {
    this.confidence = confidence;
  }

  public Boolean getNegated() {
    return negated;
  }

  public void setNegated(Boolean negated) {
    this.negated = negated;
  }

  public String getUncertainty() {
    return uncertainty;
  }

  public void setUncertainty(String uncertainty) {
    this.uncertainty = uncertainty;
  }

  public String getSection() {
    return section;
  }

  public void setSection(String section) {
    this.section = section;
  }
}
