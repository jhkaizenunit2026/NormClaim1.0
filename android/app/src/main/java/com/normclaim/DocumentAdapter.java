package com.normclaim;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.normclaim.model.DocumentInfo;
import java.util.ArrayList;
import java.util.List;

public class DocumentAdapter extends RecyclerView.Adapter<DocumentAdapter.VH> {

    public interface Listener {
        void onOpen(DocumentInfo doc);
    }

    private final List<DocumentInfo> items = new ArrayList<>();
    private final Listener listener;

    public DocumentAdapter(Listener listener) {
        this.listener = listener;
    }

    public void setItems(List<DocumentInfo> docs) {
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
        DocumentInfo d = items.get(position);
        h.filename.setText(d.filename != null ? d.filename : "(no name)");
        StringBuilder meta = new StringBuilder();
        if (Boolean.TRUE.equals(d.hasExtraction)) {
            meta.append("Extracted");
        } else {
            meta.append("Uploaded");
        }
        if (Boolean.TRUE.equals(d.hasReport)) {
            meta.append(" · Reconciled");
        }
        if (d.sizeBytes != null) {
            meta.append(" · ").append(d.sizeBytes / 1024).append(" KB");
        }
        h.meta.setText(meta.toString());
        h.itemView.setOnClickListener(v -> listener.onOpen(d));
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class VH extends RecyclerView.ViewHolder {
        final TextView filename;
        final TextView meta;

        VH(@NonNull View itemView) {
            super(itemView);
            filename = itemView.findViewById(R.id.textFilename);
            meta = itemView.findViewById(R.id.textMeta);
        }
    }
}
