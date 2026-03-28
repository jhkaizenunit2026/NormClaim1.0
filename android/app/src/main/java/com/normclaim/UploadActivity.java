package com.normclaim;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.ProgressBar;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.button.MaterialButton;
import com.normclaim.model.ExtractionResult;
import com.normclaim.model.UploadResponse;
import com.normclaim.network.ApiClient;
import com.normclaim.network.ApiService;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class UploadActivity extends AppCompatActivity {

    private ApiService api;
    private ProgressBar progress;
    private final ActivityResultLauncher<String> pickPdf =
            registerForActivityResult(new ActivityResultContracts.GetContent(), this::onPicked);

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_upload);
        api = ApiClient.get();
        progress = findViewById(R.id.progress);
        MaterialButton btn = findViewById(R.id.btnPick);
        btn.setOnClickListener(v -> pickPdf.launch("application/pdf"));
    }

    private void onPicked(Uri uri) {
        if (uri == null) {
            return;
        }
        progress.setVisibility(View.VISIBLE);
        new Thread(
                        () -> {
                            try {
                                byte[] bytes = readAll(uri);
                                runOnUiThread(() -> uploadAndPipeline(bytes, fileName(uri)));
                            } catch (Exception e) {
                                runOnUiThread(
                                        () -> {
                                            progress.setVisibility(View.GONE);
                                            Toast.makeText(
                                                            UploadActivity.this,
                                                            "Read failed: " + e.getMessage(),
                                                            Toast.LENGTH_LONG)
                                                    .show();
                                        });
                            }
                        })
                .start();
    }

    private byte[] readAll(Uri uri) throws Exception {
        try (InputStream in = getContentResolver().openInputStream(uri)) {
            if (in == null) {
                throw new IllegalStateException("no stream");
            }
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] chunk = new byte[8192];
            int n;
            while ((n = in.read(chunk)) != -1) {
                buf.write(chunk, 0, n);
            }
            return buf.toByteArray();
        }
    }

    private String fileName(Uri uri) {
        String last = uri.getLastPathSegment();
        return last != null && last.endsWith(".pdf") ? last : "upload.pdf";
    }

    private void uploadAndPipeline(byte[] bytes, String filename) {
        RequestBody body = RequestBody.create(bytes, MediaType.parse("application/pdf"));
        MultipartBody.Part part = MultipartBody.Part.createFormData("file", filename, body);

        api.uploadDocument(part)
                .enqueue(
                        new Callback<UploadResponse>() {
                            @Override
                            public void onResponse(Call<UploadResponse> call, Response<UploadResponse> response) {
                                if (!response.isSuccessful() || response.body() == null || response.body().id == null) {
                                    progress.setVisibility(View.GONE);
                                    Toast.makeText(UploadActivity.this, "Upload failed", Toast.LENGTH_LONG).show();
                                    return;
                                }
                                String id = response.body().id;
                                extractThenReconcile(id);
                            }

                            @Override
                            public void onFailure(Call<UploadResponse> call, Throwable t) {
                                progress.setVisibility(View.GONE);
                                Toast.makeText(UploadActivity.this, "Upload: " + t.getMessage(), Toast.LENGTH_LONG)
                                        .show();
                            }
                        });
    }

    private void extractThenReconcile(String docId) {
        api.runExtract(docId)
                .enqueue(
                        new Callback<ExtractionResult>() {
                            @Override
                            public void onResponse(
                                    Call<ExtractionResult> call, Response<ExtractionResult> response) {
                                if (!response.isSuccessful()) {
                                    progress.setVisibility(View.GONE);
                                    Toast.makeText(UploadActivity.this, "Extract failed", Toast.LENGTH_LONG).show();
                                    return;
                                }
                                api.runReconcile(docId)
                                        .enqueue(
                                                new Callback<com.normclaim.model.ReconciliationReport>() {
                                                    @Override
                                                    public void onResponse(
                                                            Call<com.normclaim.model.ReconciliationReport> call,
                                                            Response<com.normclaim.model.ReconciliationReport>
                                                                    r2) {
                                                        progress.setVisibility(View.GONE);
                                                        if (!r2.isSuccessful()) {
                                                            Toast.makeText(
                                                                            UploadActivity.this,
                                                                            "Reconcile failed",
                                                                            Toast.LENGTH_LONG)
                                                                    .show();
                                                            return;
                                                        }
                                                        Intent i = new Intent(UploadActivity.this, ResultActivity.class);
                                                        i.putExtra(ResultActivity.EXTRA_DOC_ID, docId);
                                                        startActivity(i);
                                                        finish();
                                                    }

                                                    @Override
                                                    public void onFailure(
                                                            Call<com.normclaim.model.ReconciliationReport> call,
                                                            Throwable t) {
                                                        progress.setVisibility(View.GONE);
                                                        Toast.makeText(
                                                                        UploadActivity.this,
                                                                        "Reconcile: " + t.getMessage(),
                                                                        Toast.LENGTH_LONG)
                                                                .show();
                                                    }
                                                });
                            }

                            @Override
                            public void onFailure(Call<ExtractionResult> call, Throwable t) {
                                progress.setVisibility(View.GONE);
                                Toast.makeText(UploadActivity.this, "Extract: " + t.getMessage(), Toast.LENGTH_LONG)
                                        .show();
                            }
                        });
    }
}

