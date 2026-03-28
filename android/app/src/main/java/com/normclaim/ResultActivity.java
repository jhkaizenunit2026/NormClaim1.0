package com.normclaim;

import android.os.Bundle;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.tabs.TabLayout;
import com.normclaim.model.Diagnosis;
import com.normclaim.model.ExtractionResult;
import com.normclaim.model.Medication;
import com.normclaim.model.ReconciliationItem;
import com.normclaim.model.ReconciliationReport;
import com.normclaim.network.ApiClient;
import com.normclaim.network.ApiService;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ResultActivity extends AppCompatActivity {

    public static final String EXTRA_DOC_ID = "docId";

    private ApiService api;
    private String docId;
    private TextView textEntities;
    private TextView textClaim;
    private ScrollView scrollEntities;
    private ScrollView scrollClaim;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_result);
        docId = getIntent().getStringExtra(EXTRA_DOC_ID);
        if (docId == null) {
            Toast.makeText(this, "Missing document id", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        api = ApiClient.get();
        textEntities = findViewById(R.id.textEntities);
        textClaim = findViewById(R.id.textClaim);
        scrollEntities = findViewById(R.id.scrollEntities);
        scrollClaim = findViewById(R.id.scrollClaim);

        TabLayout tabs = findViewById(R.id.tabLayout);
        tabs.addTab(tabs.newTab().setText("Entities"));
        tabs.addTab(tabs.newTab().setText("Claim Report"));
        tabs.addOnTabSelectedListener(
                new TabLayout.OnTabSelectedListener() {
                    @Override
                    public void onTabSelected(TabLayout.Tab tab) {
                        boolean entities = tab.getPosition() == 0;
                        scrollEntities.setVisibility(entities ? android.view.View.VISIBLE : android.view.View.GONE);
                        scrollClaim.setVisibility(entities ? android.view.View.GONE : android.view.View.VISIBLE);
                    }

                    @Override
                    public void onTabUnselected(TabLayout.Tab tab) {}

                    @Override
                    public void onTabReselected(TabLayout.Tab tab) {}
                });

        loadAll();
    }

    private void loadAll() {
        api.getExtraction(docId)
                .enqueue(
                        new Callback<ExtractionResult>() {
                            @Override
                            public void onResponse(Call<ExtractionResult> call, Response<ExtractionResult> response) {
                                if (response.isSuccessful() && response.body() != null) {
                                    textEntities.setText(formatExtraction(response.body()));
                                } else {
                                    textEntities.setText("No extraction for this document yet.");
                                }
                            }

                            @Override
                            public void onFailure(Call<ExtractionResult> call, Throwable t) {
                                textEntities.setText("Error: " + t.getMessage());
                            }
                        });

        api.getReconcile(docId)
                .enqueue(
                        new Callback<ReconciliationReport>() {
                            @Override
                            public void onResponse(
                                    Call<ReconciliationReport> call, Response<ReconciliationReport> response) {
                                if (response.code() == 404) {
                                    runReconcilePost();
                                    return;
                                }
                                if (response.isSuccessful() && response.body() != null) {
                                    textClaim.setText(formatReport(response.body()));
                                } else {
                                    textClaim.setText("No reconciliation yet.");
                                }
                            }

                            @Override
                            public void onFailure(Call<ReconciliationReport> call, Throwable t) {
                                textClaim.setText("Error: " + t.getMessage());
                            }
                        });
    }

    private void runReconcilePost() {
        api.runReconcile(docId)
                .enqueue(
                        new Callback<ReconciliationReport>() {
                            @Override
                            public void onResponse(
                                    Call<ReconciliationReport> call, Response<ReconciliationReport> response) {
                                if (response.isSuccessful() && response.body() != null) {
                                    textClaim.setText(formatReport(response.body()));
                                } else {
                                    textClaim.setText("Run extract first (POST /api/extract).");
                                }
                            }

                            @Override
                            public void onFailure(Call<ReconciliationReport> call, Throwable t) {
                                textClaim.setText("Error: " + t.getMessage());
                            }
                        });
    }

    private static String formatExtraction(ExtractionResult e) {
        StringBuilder sb = new StringBuilder();
        if (e.patient != null) {
            sb.append("Patient: ")
                    .append(nullSafe(e.patient.name))
                    .append(" | ")
                    .append(e.patient.age != null ? e.patient.age + "y" : "")
                    .append(" ")
                    .append(nullSafe(e.patient.sex))
                    .append("\n\n");
        }
        if (e.encounter != null) {
            sb.append("Encounter: admit ")
                    .append(nullSafe(e.encounter.admitDate))
                    .append(" → discharge ")
                    .append(nullSafe(e.encounter.dischargeDate))
                    .append("\n\n");
        }
        sb.append("— Diagnoses —\n");
        if (e.diagnoses != null) {
            for (Diagnosis d : e.diagnoses) {
                sb.append(d.icd10Code)
                        .append(" ")
                        .append(nullSafe(d.icd10Display))
                        .append("\n  ")
                        .append(nullSafe(d.text))
                        .append(" | conf ")
                        .append(d.confidence != null ? d.confidence : 0)
                        .append(d.negated != null && d.negated ? " [NEGATED]" : "")
                        .append("\n\n");
            }
        }
        sb.append("— Medications —\n");
        if (e.medications != null) {
            for (Medication m : e.medications) {
                sb.append(nullSafe(m.brandName))
                        .append(" → ")
                        .append(nullSafe(m.genericName))
                        .append("\n");
            }
        }
        sb.append("\nBilled codes: ").append(e.billedCodes != null ? e.billedCodes.toString() : "[]");
        return sb.toString();
    }

    private static String formatReport(ReconciliationReport r) {
        StringBuilder sb = new StringBuilder();
        sb.append("Estimated claim delta: ₹")
                .append(r.estimatedClaimDeltaInr != null ? Math.round(r.estimatedClaimDeltaInr) : 0)
                .append("\n\n— Matched —\n");
        if (r.matched != null) {
            for (ReconciliationItem i : r.matched) {
                sb.append(i.icd10Code).append(" ").append(nullSafe(i.description)).append("\n");
            }
        }
        sb.append("\n— Missed (revenue left on table) —\n");
        if (r.missed != null) {
            for (ReconciliationItem i : r.missed) {
                sb.append(i.icd10Code)
                        .append(" ")
                        .append(nullSafe(i.description))
                        .append(" → ₹")
                        .append(i.estimatedValueInr != null ? Math.round(i.estimatedValueInr) : 0)
                        .append("\n");
            }
        }
        sb.append("\n— Extra on bill —\n");
        if (r.extra != null) {
            for (ReconciliationItem i : r.extra) {
                sb.append(i.icd10Code).append(" ").append(nullSafe(i.description)).append("\n");
            }
        }
        return sb.toString();
    }

    private static String nullSafe(String s) {
        return s != null ? s : "";
    }
}
