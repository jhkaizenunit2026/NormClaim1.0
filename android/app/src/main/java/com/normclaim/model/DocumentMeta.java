package com.normclaim.model;

import com.google.gson.annotations.SerializedName;

/**
 * Metadata for a single document. Used in list responses and detail views.
 */
public class DocumentMeta {

    @SerializedName("document_id")
    public String documentId;

    @SerializedName("filename")
    public String filename;

    @SerializedName("status")
    public String status;

    @SerializedName("uploaded_at")
    public String uploadedAt;
}
