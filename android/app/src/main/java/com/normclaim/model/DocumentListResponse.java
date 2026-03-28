package com.normclaim.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

/**
 * Response from GET /api/documents — wraps a list of DocumentMeta.
 */
public class DocumentListResponse {

    @SerializedName("documents")
    public List<DocumentMeta> documents;

    @SerializedName("total")
    public int total;
}
