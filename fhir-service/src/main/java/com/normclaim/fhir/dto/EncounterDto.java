package com.normclaim.fhir.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class EncounterDto {

  private String admitDate;
  private String dischargeDate;
  private String ward;
  private Integer losDays;

  public String getAdmitDate() {
    return admitDate;
  }

  public void setAdmitDate(String admitDate) {
    this.admitDate = admitDate;
  }

  public String getDischargeDate() {
    return dischargeDate;
  }

  public void setDischargeDate(String dischargeDate) {
    this.dischargeDate = dischargeDate;
  }

  public String getWard() {
    return ward;
  }

  public void setWard(String ward) {
    this.ward = ward;
  }

  public Integer getLosDays() {
    return losDays;
  }

  public void setLosDays(Integer losDays) {
    this.losDays = losDays;
  }
}
