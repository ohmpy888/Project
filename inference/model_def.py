# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
import torch.nn.functional as F

class CNN_BiLSTM_Attn(nn.Module):
    """
    ตรงกับรุ่นที่คุณเทรน: CNN (หลาย kernel) -> concat -> BiLSTM -> Attention -> FC
    forward คืน (logits, alpha) โดย alpha เป็น attention ต่อ time-step หลัง LSTM
    """
    def __init__(self, vocab_size, emb_dim, cnn_channels, kernel_sizes, lstm_hidden, lstm_layers, bidir, dropout, num_classes=2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(in_channels=emb_dim, out_channels=cnn_channels, kernel_size=k)
            for k in kernel_sizes
        ])
        self.relu = nn.ReLU()
        lstm_input_dim = cnn_channels * len(kernel_sizes)
        self.lstm = nn.LSTM(
            input_size=lstm_input_dim,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=bidir,
        )
        attn_dim = lstm_hidden * (2 if bidir else 1)
        self.attn_w = nn.Linear(attn_dim, 1, bias=False)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(attn_dim, num_classes)

    def forward(self, x):
        emb = self.embedding(x)                  # (B,T,E)
        emb_t = emb.transpose(1, 2)              # (B,E,T)
        conv_feats = []
        for conv in self.convs:
            c = self.relu(conv(emb_t))           # (B,C,T')
            c = c.transpose(1, 2)                # (B,T',C)
            conv_feats.append(c)
        # align time by cropping to shortest T'
        min_t = min(cf.size(1) for cf in conv_feats)
        conv_feats = [cf[:, :min_t, :] for cf in conv_feats]
        feats = torch.cat(conv_feats, dim=2)     # (B, T', C*len(K))
        lstm_out, _ = self.lstm(feats)           # (B, T', H*(2))
        alpha = self.attn_w(lstm_out)            # (B, T', 1)
        alpha = torch.softmax(alpha.squeeze(-1), dim=1)    # (B, T')
        context = torch.sum(lstm_out * alpha.unsqueeze(-1), dim=1)  # (B, 2H)
        logits = self.fc(self.dropout(context))  # (B, 2)
        return logits, alpha
