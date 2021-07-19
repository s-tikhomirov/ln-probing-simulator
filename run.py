#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.


import argparse
import time

from experiments import experiment_1, experiment_2, experiment_3
from prober import Prober


def generate_prober():
	FILENAME = "./snapshot/listchannels-2021-05-23.json"
	ENTRY_CHANNEL_CAPACITY = 10*100*1000*1000
	# top 10 nodes by degree as per https://1ml.com/node?order=channelcount
	ENTRY_NODES = [
	"02ad6fb8d693dc1e4569bcedefadf5f72a931ae027dc0f0c544b34c1c6f3b9a02b",
	"03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
	"0217890e3aad8d35bc054f43acc00084b25229ecff0ab68debd82883ad65ee8266",
	"0331f80652fb840239df8dc99205792bba2e559a05469915804c08420230e23c7c",
	"0242a4ae0c5bef18048fbecf995094b74bfb0f7391418d71ed394784373f41e4f3",
	"03bb88ccc444534da7b5b64b4f7b15e1eccb18e102db0e400d4b9cfe93763aa26d",
	"03abf6f44c355dec0d5aa155bdbdd6e0c8fefe318eff402de65c6eb2e1be55dc3e",
	"02004c625d622245606a1ea2c1c69cfb4516b703b47945a3647713c05fe4aaeb1c",
	"0395033b252c6f40e3756984162d68174e2bd8060a129c0d3462a9370471c6d28f",
	"0390b5d4492dc2f5318e5233ab2cebf6d48914881a33ef6a9c6bcdbb433ad986d0"
	]
	prober = Prober(FILENAME, "PROBER", ENTRY_NODES, ENTRY_CHANNEL_CAPACITY)
	return prober


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--num_target_hops", default=100, type=int,
		help="The number of target hops per experiment run.")
	parser.add_argument("--num_runs_per_experiment", default=10, type=int,
		help="Run the same experiment this many times (results are averaged).")
	parser.add_argument("--max_num_channels", default=10, type=int,
		help="Consider target hops with the number of channels up to this number.")
	parser.add_argument("--use_snapshot", dest="use_snapshot", action="store_true",
		help="Pick target hops from snapshot? (Then do both isolated and snapshot probing.)")
	parser.add_argument("--jamming", dest="jamming", action="store_true",
		help="Use jamming after h and g are known?")
	args = parser.parse_args()

	if args.use_snapshot and args.max_num_channels > 5:
		print("Too high max_num_channels: snapshot doesn't have that many hops with that many channels.")
		exit()

	prober = generate_prober() if args.use_snapshot else None
	
	if prober:
		prober.analyze_graph()

	experiment_1(prober, args.num_target_hops, args.num_runs_per_experiment, args.max_num_channels, args.use_snapshot, args.jamming)
	experiment_2(args.num_target_hops, args.num_runs_per_experiment)
	experiment_3(args.num_target_hops, args.num_runs_per_experiment, max_ratio=10)	


if __name__ == "__main__":
	start_time = time.time()
	main()
	end_time = time.time()
	print("Completed in", round(end_time - start_time), "seconds.")
