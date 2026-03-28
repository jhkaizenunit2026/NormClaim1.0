package com.normclaim.fhir.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class PatientDto {

  private String name;
  private Integer age;
  private String sex;
  private String abhaId;

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public Integer getAge() {
    return age;
  }

  public void setAge(Integer age) {
    this.age = age;
  }

  public String getSex() {
    return sex;
  }

  public void setSex(String sex) {
    this.sex = sex;
  }

  public String getAbhaId() {
    return abhaId;
  }

  public void setAbhaId(String abhaId) {
    this.abhaId = abhaId;
  }
}
