package com.normclaim;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.normclaim.model.DocumentInfo;
import com.normclaim.network.ApiClient;
import com.normclaim.network.ApiService;
import java.util.List;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity {

    private DocumentAdapter adapter;
    private ApiService api;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        api = ApiClient.get();

        RecyclerView rv = findViewById(R.id.recyclerDocuments);
        rv.setLayoutManager(new LinearLayoutManager(this));
        adapter = new DocumentAdapter(this::openDocument);
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
        api.listDocuments()
                .enqueue(
                        new Callback<List<DocumentInfo>>() {
                            @Override
                            public void onResponse(
                                    Call<List<DocumentInfo>> call, Response<List<DocumentInfo>> response) {
                                if (response.isSuccessful() && response.body() != null) {
                                    adapter.setItems(response.body());
                                } else {
                                    Toast.makeText(MainActivity.this, "Could not load documents", Toast.LENGTH_SHORT)
                                            .show();
                                }
                            }

                            @Override
                            public void onFailure(Call<List<DocumentInfo>> call, Throwable t) {
                                Toast.makeText(
                                                MainActivity.this,
                                                "Network error: " + t.getMessage(),
                                                Toast.LENGTH_LONG)
                                        .show();
                            }
                        });
    }

    private void openDocument(DocumentInfo doc) {
        if (doc.documentId == null) {
            return;
        }
        Intent i = new Intent(this, ResultActivity.class);
        i.putExtra(ResultActivity.EXTRA_DOC_ID, doc.documentId);
        startActivity(i);
    }
}
