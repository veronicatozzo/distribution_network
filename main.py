import os
import csv
import sys
# sys.path.append("/misc/vlgscratch5/RanganathGroup/lily/miniconda3/envs/blood_matlab/lib/python3.7/site-packages/")
import argparse
from datetime import datetime
import wandb
import numpy as np
import torch
from torch.utils.data import DataLoader

from deep_sets.models import SmallDeepSetMax, SmallDeepSetMean, SmallDeepSetSum
from set_transformer.models import SmallSetTransformer
from src.dataset import FullSampleDataset
from src.train import train_nn, train_KNNDivergence, train_distribution2distrbution, train_sklearn_moments, baseline


os.environ["WANDB_API_KEY"] = "ec22fec7bdd7579e0c42b8d29465922af4340148"  # "893130108141453e3e50e00010d3e3fced11c1e8"

parser = argparse.ArgumentParser(description='Results summary')
parser.add_argument('-i', '--inputs', metavar='N', type=str, nargs='+',
                    help='a list of strings denoting the distribution inputs')
parser.add_argument('-o', '--outputs', metavar='N', type=str, nargs='+',
                    help='a list of strings denoting the prediction outputs')
parser.add_argument('-m', '--model', type=str,
                    help='string name for model type')

parser.add_argument('--id_file', type=str, default='', help='filename of the ids to use')
parser.add_argument('--num_subsamples', type=int, default=100,
                    help='number of samples to use in each distribution. note that non-neural models use all subsamples if -1')
parser.add_argument('--permute_subsamples', dest='permute_subsamples', action='store_true')
parser.add_argument('--normalizer', type=str, help='name of the normalizer', default='all')

# Neural network hyperparameters
parser.add_argument('--batch_size', type=int, default=64)
parser.add_argument('--num_workers', type=int, default=4, help='number of cpu workers in the data loader')
parser.add_argument('--lr', type=float, default=.001)
parser.add_argument('--step_size', type=int, default=50)
parser.add_argument('--gamma', type=int, default=.1)

# KNN Divergence hyperparameters
parser.add_argument('--k', type=int, default=5)
parser.add_argument('--C', type=float, default=1.)
parser.add_argument('--div', type=str, default='kl')

parser.add_argument('--name', type=str, help='name of the experiment in wandb',
                    default='')
parser.add_argument('--save', dest='save', action='store_true', help='whether to save the model')
args = parser.parse_args()

model_dict = dict(
    SetTransformer=SmallSetTransformer,
    DeepSetsMax=SmallDeepSetMax,
    DeepSetsMean=SmallDeepSetMean,
    DeepSetsSum=SmallDeepSetSum,
)

outputs_dict = dict(
    Age={"type": "regression"},
    Hematocrit={"type": "regression"},
    Age70={"type": "classification", "num_classes": 2},
)
print(torch.cuda.is_available())

if __name__ == "__main__":
    if args.name:
        name = args.name
    else:
        name = '_'.join([args.model, ','.join(args.outputs), ','.join(args.inputs)])
    # wandb.init(project="distribution-regression", name=name)
    # wandb.init(project="blood-distribution", name=name)
    # wandb.config.update(args)

    if args.id_file:
        id_file = args.id_file
    else:
        # path_to_id_files = "/misc/vlgscratch5/RanganathGroup/lily/blood_dist/balanced_age/id_files"
        path_to_id_files = "/Users/lilyzhang/Desktop/Dropbox/Distribution-distribution regression/balanced_age/id_files"
        # path_to_id_files = "/Users/vt908/Dropbox (Partners HealthCare)/Distribution-distribution regression/balanced_age/id_lists"
        id_file = os.path.join(path_to_id_files, '_'.join([','.join(args.outputs), ','.join(args.inputs), str("{:%B-%d-%Y}.txt".format(datetime.now()))]))

    data_config = {
        'inputs': args.inputs,
        'outputs': args.outputs,
        'id_file': id_file,
        'num_subsamples': args.num_subsamples,
        'permute_subsamples': args.permute_subsamples,
        'normalizer': args.normalizer,
    }

    # dates inputs outputs
    if len(args.inputs) > 1 and len(args.num_subsamples) == -1:
        raise NotImplemented("Cannot support multiple distributions with differential numbers of subsamples")
    if len(args.inputs) > 1 and args.model in ['KNNDiv', 'DistReg']:
        raise NotImplemented("Cannot support multiple distributions with KNNDiv and DistReg")
    train_data = FullSampleDataset(test=False, **data_config)
    test_data = FullSampleDataset(test=True, **data_config)
    print("Missing inputs in train: ", train_data.missing_inputs)
    print("Missing inputs in test: ", test_data.missing_inputs)
    if args.model in ['KNNDiv', 'DistReg', 'KNN', 'RF', 'GBC', 'RR', 'baseline']:
        X_tr, y_tr = zip(*[train_data[i] for i in range(len(train_data))])
        X_ts, y_ts = zip(*[test_data[i] for i in range(len(test_data))])
        if len(args.outputs) > 1:
            raise NotImplemented("KNNDiv doesn't work for multi-outputs")
        X_tr = np.array(list(X_tr))
        X_ts = np.array(list(X_ts))
        y_tr = np.array(list(y_tr))
        y_ts = np.array(list(y_ts))
        print(y_tr)
        print(X_tr.shape)
        if args.model == 'KNNDiv':
            train_score, test_score = train_KNNDivergence(args.div, X_tr, y_tr, X_ts, y_ts, args.k, args.C, name=name)
        elif args.model == 'DistReg':
            y_tr = y_tr.flatten()
            y_ts = y_ts.flatten()
            train_score, test_score = train_distribution2distrbution(X_tr, y_tr, X_ts, y_ts, name=name)
        elif args.model in ['KNN', 'RF', 'GBC', 'RR']:
            train_score, test_score = train_sklearn_moments(X_tr, y_tr, X_ts, y_ts, name=name, model=args.model)
        elif args.model == 'baseline':
            train_score, test_score = baseline(y_tr, y_ts)
        with open('baselines.csv', 'a') as f:
            writer = csv.writer(f)
            writer.writerow([','.join(args.inputs), ','.join(args.outputs), args.model, args.div, args.k, args.C, train_score, test_score])
    else:
        train_generator = DataLoader(train_data,
                                batch_size=args.batch_size,
                                shuffle=True,
                                num_workers=args.num_workers,
                                pin_memory=False,
                                drop_last=True)
        test_generator = DataLoader(test_data,
                                batch_size=args.batch_size,
                                shuffle=True,
                                num_workers=args.num_workers,
                                pin_memory=False,
                                drop_last=True)
        
        model_params = {'n_outputs': len(args.outputs), 'n_inputs': len(args.inputs)}
        model = model_dict[args.model](**model_params)
        optimizer = torch.optim.Adam(model.parameters(),lr=args.lr)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=args.step_size, gamma=args.gamma, last_epoch=-1)
        model = train_nn(model, args.name, optimizer, scheduler, train_generator, test_generator)
        if args.save:
            torch.save(model, args.name + '.pt')
