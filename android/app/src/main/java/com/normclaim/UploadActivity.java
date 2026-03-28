package com.normclaim;

import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.View;
import android.widget.ImageButton;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;
import com.google.android.material.checkbox.MaterialCheckBox;
import com.normclaim.model.DocumentUploadResponse;
import com.normclaim.network.RetrofitClient;
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
    private MaterialButton btnUpload;
    private MaterialCheckBox checkConsent;
    private MaterialCardView cardPreview;
    private TextView textSelectedFilename, textSelectedFileSize;
    
    private Uri selectedFileUri = null;
    private long selectedFileSize = 0;

    private final ActivityResultLauncher<String> pickPdf =
            registerForActivityResult(new ActivityResultContracts.GetContent(), this::onPicked);

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_upload);
        
        api = RetrofitClient.get();
        progress = findViewById(R.id.progressUpload);
        btnUpload = findViewById(R.id.btnUpload);
        checkConsent = findViewById(R.id.checkConsent);
        cardPreview = findViewById(R.id.cardPreview);
        textSelectedFilename = findViewById(R.id.textSelectedFilename);
        textSelectedFileSize = findViewById(R.id.textSelectedFileSize);
        ImageButton btnRemove = findViewById(R.id.btnRemoveFile);

        findViewById(R.id.cardPick).setOnClickListener(v -> pickPdf.launch("application/pdf"));
        
        btnRemove.setOnClickListener(v -> removeFile());
        
        checkConsent.setOnCheckedChangeListener((buttonView, isChecked) -> validateForm());
        
        btnUpload.setOnClickListener(v -> uploadFile());
        
        androidx.appcompat.widget.Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        if (getSupportActionBar() != null) {
            getSupportActionBar().setDisplayHomeAsUpEnabled(true);
            getSupportActionBar().setDisplayShowHomeEnabled(true);
        }
        toolbar.setNavigationOnClickListener(v -> finish());
    }

    private void onPicked(Uri uri) {
        if (uri == null) return;
        
        try {
            String name = "file.pdf";
            long size = 0;
            
            Cursor cursor = getContentResolver().query(uri, null, null, null, null);
            if (cursor != null && cursor.moveToFirst()) {
                int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                int sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE);
                if (nameIndex != -1) name = cursor.getString(nameIndex);
                if (sizeIndex != -1) size = cursor.getLong(sizeIndex);
                cursor.close();
            }

            if (size > 20 * 1024 * 1024) {
                Toast.makeText(this, "File too large (Max 20MB)", Toast.LENGTH_LONG).show();
                return;
            }

            selectedFileUri = uri;
            selectedFileSize = size;
            
            textSelectedFilename.setText(name);
            textSelectedFileSize.setText(formatSize(size));
            cardPreview.setVisibility(View.VISIBLE);
            
            validateForm();
            
        } catch (Exception e) {
            Toast.makeText(this, "Error selecting file", Toast.LENGTH_SHORT).show();
        }
    }

    private void removeFile() {
        selectedFileUri = null;
        selectedFileSize = 0;
        cardPreview.setVisibility(View.GONE);
        checkConsent.setChecked(false);
        validateForm();
    }

    private void validateForm() {
        btnUpload.setEnabled(selectedFileUri != null && checkConsent.isChecked());
    }

    private void uploadFile() {
        if (selectedFileUri == null) return;

        progress.setVisibility(View.VISIBLE);
        btnUpload.setEnabled(false);
        btnUpload.setText("Uploading...");

        new Thread(() -> {
            try {
                byte[] bytes = readAll(selectedFileUri);
                runOnUiThread(() -> performRequest(bytes));
            } catch (Exception e) {
                runOnUiThread(() -> {
                    progress.setVisibility(View.GONE);
                    btnUpload.setEnabled(true);
                    btnUpload.setText("Upload & Begin Extraction");
                    Toast.makeText(this, "Read error: " + e.getMessage(), Toast.LENGTH_LONG).show();
                });
            }
        }).start();
    }

    private void performRequest(byte[] bytes) {
        String filename = textSelectedFilename.getText().toString();
        RequestBody fileBody = RequestBody.create(bytes, MediaType.parse("application/pdf"));
        MultipartBody.Part filePart = MultipartBody.Part.createFormData("file", filename, fileBody);
        
        // consent_obtained must be sent as RequestBody for multipart
        RequestBody consentPart = RequestBody.create("true", MediaType.parse("text/plain"));

        api.uploadDocument(filePart, consentPart).enqueue(new Callback<DocumentUploadResponse>() {
            @Override
            public void onResponse(Call<DocumentUploadResponse> call, Response<DocumentUploadResponse> response) {
                progress.setVisibility(View.GONE);
                if (response.isSuccessful() && response.body() != null) {
                    Toast.makeText(UploadActivity.this, "Uploaded! Starting extraction...", Toast.LENGTH_SHORT).show();
                    Intent intent = new Intent(UploadActivity.this, ResultActivity.class);
                    // Pass documentId from DocumentUploadResponse
                    intent.putExtra(ResultActivity.EXTRA_DOC_ID, response.body().documentId);
                    startActivity(intent);
                    finish();
                } else {
                    btnUpload.setEnabled(true);
                    btnUpload.setText("Upload & Begin Extraction");
                    try {
                        String errorBody = response.errorBody() != null ? response.errorBody().string() : "Unknown Error";
                        Toast.makeText(UploadActivity.this, "Upload failed: " + errorBody, Toast.LENGTH_LONG).show();
                    } catch (Exception e) {
                        Toast.makeText(UploadActivity.this, "Upload failed: Status " + response.code(), Toast.LENGTH_LONG).show();
                    }
                }
            }

            @Override
            public void onFailure(Call<DocumentUploadResponse> call, Throwable t) {
                progress.setVisibility(View.GONE);
                btnUpload.setEnabled(true);
                btnUpload.setText("Upload & Begin Extraction");
                Toast.makeText(UploadActivity.this, "Network: " + t.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    private byte[] readAll(Uri uri) throws Exception {
        try (InputStream in = getContentResolver().openInputStream(uri)) {
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] chunk = new byte[8192];
            int n;
            while ((n = in.read(chunk)) != -1) buf.write(chunk, 0, n);
            return buf.toByteArray();
        }
    }

    private static String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        int exp = (int) (Math.log(bytes) / Math.log(1024));
        String pre = "KMGTPE".charAt(exp - 1) + "";
        return String.format("%.1f %sB", bytes / Math.pow(1024, exp), pre);
    }
}
