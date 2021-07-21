# Lightning Network Probing Simulator

This simulator accompanies the paper "Analysis and Probing of Parallel Channels in the Lightning Network".

Requires `python3`, `networkx`, `matplotlib`.

Usage example:

```
./run.py --num_runs_per_experiment=3 --num_target_hops=10 --max_num_channels=5 --jamming --use_snapshot
```

Run `./run.py -h` for details.
