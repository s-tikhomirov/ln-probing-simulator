# ln-probing-simulator

Usage example:

```
./run.py --use_snapshot --num_snapshot_runs=10 --num_hops=10 --save_figures
```

Parameters:

* `use_snapshot` - whether to run experiments on the real snapshot (or only on synthetic hops)
* `num_snapshot_runs` - the number of snapshot experiments. More experiments take longer but result in less variance (error bars)
* `num_hops` - the number of target hops for each experiment
* `save_figures` - whether to save the resulting figures in `/results` directory