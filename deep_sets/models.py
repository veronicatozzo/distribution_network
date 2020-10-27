import torch.nn as nn


class SmallDeepSet(nn.Module):
    def __init__(self, n_outputs=1, **kwargs):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Linear(in_features=2, out_features=64),
            nn.ReLU(),
            nn.Linear(in_features=64, out_features=64),
            nn.ReLU(),
            nn.Linear(in_features=64, out_features=64),
            nn.ReLU(),
            nn.Linear(in_features=64, out_features=64),
        )
        self.dec = nn.Sequential(
            nn.Linear(in_features=64, out_features=64),
            nn.ReLU(),
            nn.Linear(in_features=64, out_features=n_outputs),
        )

    def forward(self, x):
        if x.shape[1] > 1:
            raise NotImplemented("Can't handle multiple inputs")
        else:
            x = x.squeeze(1)
        return x

class SmallDeepSetMax(SmallDeepSet):
    def forward(self, x):
        x = super().forward(x)
        x = self.enc(x)
        x = x.max(dim=-2)[0]
        x = self.dec(x)
        return x

class SmallDeepSetMean(SmallDeepSet):
    def forward(self, x):
        x = super().forward(x)
        x = self.enc(x)
        x = x.mean(dim=-2)[0]
        x = self.dec(x)
        return x

class SmallDeepSetSum(SmallDeepSet):
    def forward(self, x):
        x = super().forward(x)
        x = self.enc(x)
        x = x.sum(dim=-2)[0]
        x = self.dec(x)
        return x
