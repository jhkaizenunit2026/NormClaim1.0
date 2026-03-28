package com.normclaim;

import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.normclaim.model.DocumentMeta;
import java.util.ArrayList;
import java.util.List;

/**
 * Adapter for the recent documents list.
 */
public class DocumentAdapter extends RecyclerView.Adapter<DocumentAdapter.VH> {

    public interface Listener {
        void onOpen(DocumentMeta doc);
    }

    private final List<DocumentMeta> items = new ArrayList<>();
    private final Listener listener;

    public DocumentAdapter(Listener listener) {
        this.listener = listener;
    }

    public void setItems(List<DocumentMeta> docs) {
        items.clear();
        if (docs != null) {
            items.addAll(docs);
        }
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_document, parent, false);
        return new VH(v);
    }

    @Override
    public void onBindViewHolder(@NonNull VH h, int position) {
        DocumentMeta d = items.get(position);
        h.filename.setText(d.filename != null ? d.filename : "unnamed_document.pdf");
        
        String status = d.status != null ? d.status : "uploaded";
        h.status.setText(status.replace("_", " ").toUpperCase());
        
        // Color coding for status
        switch (status) {
            case "reconciled":
                h.status.setTextColor(Color.parseColor("#16A34A"));
                break;
            case "extracted":
                h.status.setTextColor(Color.parseColor("#2563EB"));
                break;
            case "fhir_generated":
                h.status.setTextColor(Color.parseColor("#7C3AED"));
                break;
            default:
                h.status.setTextColor(Color.parseColor("#8899AA"));
                break;
        }

        if (d.uploadedAt != null) {
            h.date.setText(formatDate(d.uploadedAt));
        }

        h.itemView.setOnClickListener(v -> listener.onOpen(d));
        h.btnView.setOnClickListener(v -> listener.onOpen(d));
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    private String formatDate(String iso) {
        try {
            // Simple string slice for "2026-03-28T10:30:00Z" -> "28 Mar"
            String day = iso.substring(8, 10);
            String monthNum = iso.substring(5, 7);
            String[] months = {"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"};
            int mIdx = Integer.parseInt(monthNum) - 1;
            return day + " " + months[mIdx];
        } catch (Exception e) {
            return "";
        }
    }

    static class VH extends RecyclerView.ViewHolder {
        final TextView filename;
        final TextView status;
        final TextView date;
        final View btnView;

        VH(@NonNull View itemView) {
            super(itemView);
            filename = itemView.findViewById(R.id.textFilename);
            status = itemView.findViewById(R.id.textStatus);
            date = itemView.findViewById(R.id.textDate);
            btnView = itemView.findViewById(R.id.btnView);
        }
    }
}
