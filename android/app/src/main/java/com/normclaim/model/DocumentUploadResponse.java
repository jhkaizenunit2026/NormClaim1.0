package com.normclaim.model;

import com.google.gson.annotations.SerializedName;

/**
 * Response from POST /api/documents.
 */
public class DocumentUploadResponse {

    @SerializedName("document_id")
    public String documentId;

    @SerializedName("filename")
    public String filename;

    @SerializedName("status")
    public String status;

    @SerializedName("consent_obtained")
    public boolean consentObtained;

    @SerializedName("uploaded_at")
    public String uploadedAt;

    @SerializedName("message")
    public String message;
}
