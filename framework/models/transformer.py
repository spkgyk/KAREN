import torch
import torch.nn as nn
import math

from ..base_model import BaseModel
from ..register_model import RegisterModel

class PositionalEncoding(nn.Module):

    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term_sin = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        div_term_cos = torch.exp(torch.arange(1, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term_sin)
        pe[:, 1::2] = torch.cos(position * div_term_cos)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)


@RegisterModel('Transformer')
class Transformer(BaseModel):
    """
        Simple transformer model for prediction

        Because this is a multi-class classification model, no decoder part is used consisting only of an encoder module replicated multiple times

        Allows for usage of pre-trained word embeddings
    """

    def __init__(self, in_feat, out_feat, hidden_size, n_heads, n_layers, embeddings, dropout, batch_size):
        super(Transformer, self).__init__()
        self.embeddings = embeddings
        size = self.embeddings.weight.shape[-1]
        
        self.pos_encoding = PositionalEncoding(size, dropout=dropout, max_len=batch_size)

        encoder = nn.TransformerEncoderLayer(
            size, n_heads, dim_feedforward=hidden_size, dropout=dropout)

        self.model = nn.TransformerEncoder(encoder, n_layers)
        self.linear = nn.Linear(in_feat*size, out_feat)

    def forward(self, data):
        src = self.embeddings(data['tokens']).float()
        src = src.reshape(src.shape[1], src.shape[0], src.shape[2])
        src = self.pos_encoding(src)
        out = self.model(src, src_key_padding_mask=~data['mask'])
        out = out.reshape(out.shape[1], -1)
        return self.linear(out)

    @staticmethod
    def add_required_arguments(parser):
        group = parser.add_argument_group()

        group.add_argument('--transformer-hidden-size', type=int, default=2048,
                           help='Size of the feedforward network model inside the encoder layer')
        group.add_argument('--transformer-n-heads', type=int, default=8,
                           help='Number of multiheadattention in each encoder layer.')
        group.add_argument('--transformer-n-layers', type=int, default=4,
                           help='The number of encoder layers to be stacked')

    @staticmethod
    def make_model(args):
        if args.embeddings is not None:
            embeddings = nn.Embedding.from_pretrained(
                torch.tensor(args.embeddings))
        else:
            embeddings = nn.Embedding(args.vocab_size, args.embedding_dim)

        return Transformer(args.in_feat, args.out_feat, args.transformer_hidden_size,
                        args.transformer_n_heads, args.transformer_n_layers, embeddings, args.dropout, args.batch_size)

    @staticmethod
    def data_requirements():
        return ['tokens', 'mask']