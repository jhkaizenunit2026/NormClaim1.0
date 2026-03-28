package com.normclaim.fhir.controller;

import ca.uhn.fhir.context.FhirContext;
import com.normclaim.fhir.dto.ExtractionInputDto;
import com.normclaim.fhir.service.BundleBuilderService;
import org.hl7.fhir.r4.model.Bundle;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/fhir")
public class FhirController {

  private final BundleBuilderService bundleBuilderService;
  private final FhirContext fhirContext = FhirContext.forR4();

  public FhirController(BundleBuilderService bundleBuilderService) {
    this.bundleBuilderService = bundleBuilderService;
  }

  @GetMapping("/health")
  public ResponseEntity<String> health() {
    return ResponseEntity.ok("ok");
  }

  @PostMapping(
      value = "/bundle",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public ResponseEntity<String> buildBundle(@RequestBody ExtractionInputDto body) {
    Bundle bundle = bundleBuilderService.build(body);
    String json =
        fhirContext.newJsonParser().setPrettyPrint(false).encodeResourceToString(bundle);
    return ResponseEntity.ok(json);
  }
}
