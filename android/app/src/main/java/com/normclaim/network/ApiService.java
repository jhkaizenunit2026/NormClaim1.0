package com.normclaim.network;

import com.normclaim.model.DocumentListResponse;
import com.normclaim.model.DocumentMeta;
import com.normclaim.model.DocumentUploadResponse;
import com.normclaim.model.ExtractionResult;
import com.normclaim.model.ReconciliationReport;

import java.util.Map;

import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.DELETE;
import retrofit2.http.GET;
import retrofit2.http.Multipart;
import retrofit2.http.POST;
import retrofit2.http.Part;
import retrofit2.http.Path;

/**
 * Retrofit interface for the NormClaim API.
 * Defines all endpoints the Android app uses.
 */
public interface ApiService {

    // ── Documents ──────────────────────────────────────────────────────

    @Multipart
    @POST("api/documents")
    Call<DocumentUploadResponse> uploadDocument(
            @Part MultipartBody.Part file,
            @Part("consent_obtained") RequestBody consentObtained
    );

    @GET("api/documents")
    Call<DocumentListResponse> listDocuments();

    @GET("api/documents/{id}")
    Call<DocumentMeta> getDocumentMeta(@Path("id") String id);

    @DELETE("api/documents/{id}")
    Call<Map<String, String>> deleteDocument(@Path("id") String id);

    // ── Extraction ────────────────────────────────────────────────────

    @POST("api/extract/{id}")
    Call<ExtractionResult> runExtract(@Path("id") String id);

    @GET("api/extract/{id}")
    Call<ExtractionResult> getExtraction(@Path("id") String id);

    // ── FHIR ──────────────────────────────────────────────────────────

    @POST("api/fhir/{id}")
    Call<ResponseBody> generateFhir(@Path("id") String id);

    // ── Reconciliation ────────────────────────────────────────────────

    @POST("api/reconcile/{id}")
    Call<ReconciliationReport> runReconcile(@Path("id") String id);

    @GET("api/reconcile/{id}")
    Call<ReconciliationReport> getReconcile(@Path("id") String id);
}
