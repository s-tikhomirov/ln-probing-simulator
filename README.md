# Lightning Network Probing Simulator

This simulator accompanies the paper "[Analysis and Probing of Parallel Channels in the Lightning Network](https://eprint.iacr.org/2021/384)" by Alex Biryukov, Gleb Naumenko, and Sergei Tikhomirov.

Requirements: `python3`, `networkx`, `matplotlib`.

Run `run.py` to print stats about the LN graph and launch two experiments based on the snapshot given in `snapshots/`. The first experiment measures information gain and probing speed for all parameter combinations (with / without jamming; direct / remote probing; BS / NBS probe amount selection). The results are saved as plots in `results/`. The second experiments measures information gain and probing speed for all configurations of two-channel hops (large / small channels, enabled / disabled in different directions). The results are presented as CLI output.

Usage example:

```
./run.py --num_target_hops=20 --num_runs_per_experiment=10 --min_num_channels=1 --max_num_channels=5 --use_snapshot --jamming
```

Run `./run.py -h` for details.

The results in the paper were obtained as follows (running time approximately 1 hour):

```
./run.py --num_target_hops=20 --num_runs_per_experiment=50 --min_num_channels=1 --max_num_channels=5 --use_snapshot
./run.py --num_target_hops=20 --num_runs_per_experiment=50 --min_num_channels=1 --max_num_channels=5 --use_snapshot --jamming
```

For the 2021-09 version, the snapshot from 2021-09-09 was used.
