package com.normclaim.network;

import com.normclaim.model.DocumentInfo;
import com.normclaim.model.ExtractionResult;
import com.normclaim.model.ReconciliationReport;
import com.normclaim.model.UploadResponse;
import java.util.List;
import okhttp3.MultipartBody;
import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Multipart;
import retrofit2.http.POST;
import retrofit2.http.Part;
import retrofit2.http.Path;

public interface ApiService {

    @Multipart
    @POST("api/documents")
    Call<UploadResponse> uploadDocument(@Part MultipartBody.Part file);

    @POST("api/extract/{id}")
    Call<ExtractionResult> runExtract(@Path("id") String id);

    @GET("api/extract/{id}")
    Call<ExtractionResult> getExtraction(@Path("id") String id);

    @POST("api/reconcile/{id}")
    Call<ReconciliationReport> runReconcile(@Path("id") String id);

    @GET("api/reconcile/{id}")
    Call<ReconciliationReport> getReconcile(@Path("id") String id);

    @GET("api/documents")
    Call<List<DocumentInfo>> listDocuments();
}
