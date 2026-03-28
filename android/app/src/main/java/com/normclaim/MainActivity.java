package com.normclaim;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.ProgressBar;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.normclaim.model.DocumentListResponse;
import com.normclaim.model.DocumentMeta;
import com.normclaim.network.RetrofitClient;
import com.normclaim.network.ApiService;
import java.util.ArrayList;
import java.util.List;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity {

    private DocumentAdapter adapter;
    private ApiService api;
    private View layoutEmpty;
    private ProgressBar progress;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // Use RetrofitClient which was created in Step 10
        api = RetrofitClient.get();
        layoutEmpty = findViewById(R.id.layoutEmpty);
        progress = findViewById(R.id.progressMain);

        RecyclerView rv = findViewById(R.id.recyclerDocuments);
        rv.setLayoutManager(new LinearLayoutManager(this));
        adapter = new DocumentAdapter(new DocumentAdapter.Listener() {
            @Override
            public void onOpen(DocumentMeta doc) {
                MainActivity.this.openDocument(doc);
            }
        });
        rv.setAdapter(adapter);

        FloatingActionButton fab = findViewById(R.id.fabUpload);
        fab.setOnClickListener(v -> startActivity(new Intent(this, UploadActivity.class)));
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshList();
    }

    private void refreshList() {
        progress.setVisibility(View.VISIBLE);
        api.listDocuments().enqueue(new Callback<DocumentListResponse>() {
            @Override
            public void onResponse(Call<DocumentListResponse> call, Response<DocumentListResponse> response) {
                progress.setVisibility(View.GONE);
                if (response.isSuccessful() && response.body() != null) {
                    List<DocumentMeta> docs = response.body().documents;
                    adapter.setItems(docs);
                    layoutEmpty.setVisibility(docs == null || docs.isEmpty() ? View.VISIBLE : View.GONE);
                } else {
                    Toast.makeText(MainActivity.this, "Could not load documents", Toast.LENGTH_SHORT).show();
                    layoutEmpty.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public void onFailure(Call<DocumentListResponse> call, Throwable t) {
                progress.setVisibility(View.GONE);
                Toast.makeText(MainActivity.this, "Network error: " + t.getMessage(), Toast.LENGTH_LONG).show();
                layoutEmpty.setVisibility(View.VISIBLE);
            }
        });
    }

    private void openDocument(DocumentMeta doc) {
        if (doc.documentId == null) return;
        Intent i = new Intent(this, ResultActivity.class);
        i.putExtra(ResultActivity.EXTRA_DOC_ID, doc.documentId);
        startActivity(i);
    }
}
