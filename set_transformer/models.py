import torch.nn as nn

from set_transformer.modules import SAB, PMA

class SmallSetTransformer(nn.Module):
    def __init__(self, n_outputs=1, n_inputs=1, n_enc_layers=2, n_hidden_units=64, n_dec_layers=2, **kwargs):
        super().__init__()
        num_heads = n_inputs * 4
        enc_layers = []
        enc_layers.append(SAB(dim_in=2, dim_out=n_hidden_units, num_heads=num_heads))
        for i in range(n_enc_layers - 1):
            enc_layers.append(SAB(dim_in=n_hidden_units, dim_out=n_hidden_units, num_heads=num_heads))
        self.enc = nn.Sequential(*enc_layers)
        dec_layers = []
        for j in range(n_dec_layers - 1):
            dec_layers.append(PMA(dim=n_hidden_units, num_heads=num_heads, num_seeds=1))
        dec_layers.append(nn.Linear(in_features=n_hidden_units, out_features=n_outputs))
        self.dec = nn.Sequential(*dec_layers)

    def forward(self, x):
        if x.shape[1] > 1:
            raise NotImplemented("Can't handle multiple inputs")
            batch, n_dists, n_samples, n_feats = x.shape
            x = x.reshape(batch, n_dists * n_samples, n_feats)
        else:
            x = x.squeeze(1)
        x = self.enc(x)
        x = self.dec(x)
        # TODO: change squeeze(1) for multiple inputs
        return x.squeeze(-1).squeeze(1)
