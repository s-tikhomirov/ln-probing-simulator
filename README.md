# ln-probing-simulator

Usage example:

```
./run.py --use_snapshot --num_runs_per_experiment=10 --num_target_hops=10 --save_figures
```

Parameters:

* `use_snapshot` - whether to run experiments on the real snapshot (or only on synthetic hops)
* `num_runs_per_experiment` - the number of runs per one experiment. More runs take longer but result in less variance (error bars)
* `num_target_hops` - the number of target hops for each experiment
* `save_figures` - whether to save the resulting figures in `/results` directory